"""Physical Markdown block boundaries with original source offsets."""

from bisect import bisect_right
from collections.abc import Callable
from dataclasses import dataclass
from re import Pattern

from ..constants import (
    COMPILED_ATX_START_REGEX,
    COMPILED_CONTAINER_LIST_REGEX,
    COMPILED_DOCUMENT_BREAK_REGEX,
    COMPILED_DOCUMENT_FENCE_REGEX,
    COMPILED_DOCUMENT_TAG_REGEX,
    COMPILED_PHYSICAL_LINE_END_REGEX,
    COMPILED_REFERENCE_PREFIX_REGEX,
    COMPILED_SETEXT_REGEX,
)


HTML_BLOCK_TAGS = frozenset(
    [
        "address",
        "article",
        "aside",
        "base",
        "basefont",
        "blockquote",
        "body",
        "caption",
        "center",
        "col",
        "colgroup",
        "dd",
        "details",
        "dialog",
        "dir",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "frame",
        "frameset",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "head",
        "header",
        "hr",
        "html",
        "iframe",
        "legend",
        "li",
        "link",
        "main",
        "menu",
        "menuitem",
        "nav",
        "noframes",
        "ol",
        "optgroup",
        "option",
        "p",
        "param",
        "search",
        "section",
        "summary",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "title",
        "tr",
        "track",
        "ul",
    ]
)


@dataclass(frozen=True)
class PhysicalLine:
    """One CRLF, LF or CR line in the original source."""

    start: int
    content_end: int
    end: int


def physical_lines(text: str) -> list[PhysicalLine]:
    """Index physical Markdown lines without normalizing marker text."""
    lines: list[PhysicalLine] = []
    start = 0
    for ending in COMPILED_PHYSICAL_LINE_END_REGEX.finditer(text):
        lines.append(PhysicalLine(start, ending.start(), ending.end()))
        start = ending.end()
    lines.append(PhysicalLine(start, len(text), len(text)))
    return lines


def container_opening(line: str) -> tuple[int, tuple[int, ...]]:
    """Read only explicit quote/list prefixes, leaving ordinary indentation."""
    at = 0
    steps: list[int] = []
    while at < len(line):
        before_space = at
        while at - before_space < 3 and at < len(line) and line[at] == " ":
            at += 1
        if at < len(line) and line[at] == ">":
            steps.append(0)
            at += 1
            if at < len(line) and line[at] in " \t":
                at += 1
            continue
        marker = COMPILED_CONTAINER_LIST_REGEX.match(line, at)
        if marker is None:
            return before_space, tuple(steps)
        at = marker.end()
        padding_start = at
        while at < len(line) and line[at] in " \t":
            at += 1
        if at - padding_start > 4:
            at = padding_start + 1
        columns = 0
        for character in line[before_space:at]:
            columns += 4 - columns % 4 if character == "\t" else 1
        steps.append(columns)
    return at, tuple(steps)


def fence_opening(line: str) -> tuple[str, int, tuple[int, ...]] | None:
    """Use zero for a quote step and a column count for a list step."""
    at, steps = container_opening(line)
    before = at
    while at - before < 3 and at < len(line) and line[at] == " ":
        at += 1
    fence = COMPILED_DOCUMENT_FENCE_REGEX.match(line, at)
    if fence is None:
        return None
    run = fence.group(1) or fence.group(3)
    return run[0], len(run), steps


def container_content_start(line: str, steps: tuple[int, ...], *, partial: bool = False) -> int | None:
    """Match the opening quote/list containers on a continuation line."""
    at = 0
    for step in steps:
        if step == 0:
            before = at
            while at - before < 3 and at < len(line) and line[at] == " ":
                at += 1
            if at >= len(line) or line[at] != ">":
                return at if partial and at == len(line) else None
            at += 1
            if at < len(line) and line[at] in " \t":
                at += 1
        else:
            columns = 0
            while columns < step:
                if at >= len(line) or line[at] not in " \t":
                    return at if partial and at == len(line) else None
                columns += 4 - columns % 4 if line[at] == "\t" else 1
                at += 1
    return at


@dataclass(frozen=True)
class BlockSpan:
    """An owned literal region and its local example boundaries."""

    end: int
    opening_end: int
    body_end: int
    marker: str = ""
    size: int = 0
    steps: tuple[int, ...] = ()
    closed: bool = False


class DocumentBlocks:
    """Read the block boundaries needed by variable document scanners."""

    def __init__(self, text: str, html: Pattern[str]) -> None:
        """Index once using the caller's existing native HTML grammar."""
        self.text = text
        self.html_pattern = html
        self._html_last_ends: dict[str, int] | None = None
        self.lines = physical_lines(text)
        self.closed_fence_lines: set[int] = set()
        self.closed_html_lines: set[int] = set()
        self.content_starts = [line.start for line in self.lines]
        self.container_steps: list[tuple[int, ...]] = [() for _ in self.lines]
        self.container_paragraphs = self._container_paragraphs()
        self.starts = [line.start for line in self.lines]
        self.by_start = {line.start: index for index, line in enumerate(self.lines)}

    def line_at(self, offset: int) -> PhysicalLine:
        """Return the original physical line containing an offset."""
        return self.lines[max(0, bisect_right(self.starts, offset) - 1)]

    def blank(self, index: int) -> bool:
        """Test Markdown blank padding rather than all Unicode whitespace."""
        return not self.projected_line(index).strip(" \t")

    def projected_line(self, index: int) -> str:
        """Read native block context after its container prefix at original offsets."""
        return self.text[self.content_starts[index] : self.lines[index].content_end]

    def fence(self, start: int, *, final: bool = True) -> BlockSpan | None:
        """Read plain or quote/list-contained fenced code."""
        index = self.by_start.get(start)
        if index is None:
            return None
        first = self.lines[index]
        opening = fence_opening(self.text[start : first.content_end])
        if opening is None:
            return None
        marker, size, steps = opening
        previous = first
        for line in self.lines[index + 1 :]:
            value = self.text[line.start : line.content_end]
            content = container_content_start(value, steps)
            if content is None:
                if not final and line.end == line.content_end == len(self.text) and container_content_start(value, steps, partial=True) is not None:
                    return BlockSpan(len(self.text), first.end, len(self.text), marker, size, steps)
                if not value.strip(" \t"):
                    continue
                return BlockSpan(previous.content_end, first.end, previous.content_end, marker, size, steps)
            candidate = value[content:].lstrip(" ")
            if len(value[content:]) - len(candidate) <= 3:
                run = candidate.rstrip(" \t")
                if len(run) >= size and run == marker * len(run):
                    self.closed_fence_lines.add(line.start)
                    return BlockSpan(line.content_end, first.end, line.start, marker, size, steps, closed=True)
            previous = line
        return BlockSpan(len(self.text), first.end, len(self.text), marker, size, steps)

    def terminated_html(self, start: int) -> BlockSpan | None:
        """Keep complete native HTML blocks 2-5 through their closing physical line."""
        if start not in self.by_start:
            return None
        at = start
        while at < min(start + 3, len(self.text)) and self.text[at] == " ":
            at += 1
        special = self.text.startswith(("<!--", "<?", "<![CDATA["), at)
        declaration = self.text.startswith("<!", at) and at + 2 < len(self.text) and self.text[at + 2].isascii() and self.text[at + 2].isalpha()
        if not special and not declaration:
            return None
        if self.text.startswith("<!--", at):
            closing = ">" if self.text.startswith(("<!-->", "<!--->"), at) else "-->"
        elif self.text.startswith("<?", at):
            closing = "?>"
        elif self.text.startswith("<![CDATA[", at):
            closing = "]]>"
        else:
            closing = ">"
        if self._html_last_ends is None:
            self._html_last_ends = {ending: self.text.rfind(ending) for ending in (">", "-->", "?>", "]]>")}
        if self._html_last_ends[closing] < at:
            return None
        token = self.html_pattern.match(self.text, at)
        if token is None:
            return None
        end = self.line_at(token.end()).content_end
        return BlockSpan(end, token.end(), end, closed=True)

    def ordinary_html(self, start: int) -> BlockSpan | None:
        """Bound native type-six/seven HTML blocks at the first blank line."""
        index = self.by_start.get(start)
        if index is None:
            return None
        first = self.lines[index]
        content_start = self.content_starts[index]
        opening = COMPILED_DOCUMENT_TAG_REGEX.match(self.text[content_start : first.content_end])
        if opening is None:
            return None
        tag_start = self.text.find("<", content_start, first.content_end)
        block_tag = opening.group(1).lower() in HTML_BLOCK_TAGS
        if not block_tag and index and not self.blank(index - 1):
            return None
        token = self.html_pattern.match(self.text, tag_start)
        token_end = token.end() if token is not None else start
        if not block_tag and (token is None or token_end > first.content_end or self.text[token_end : first.content_end].strip(" \t")):
            return None
        previous = self.line_at(token_end)
        scan = max(index + 1, self.by_start.get(previous.start, index))
        for at in range(scan, len(self.lines)):
            line = self.lines[at]
            steps = self.container_steps[index]
            outside = steps and container_content_start(self.text[line.start : line.content_end], steps) is None
            if line.start >= token_end and (self.blank(at) or outside):
                return BlockSpan(previous.content_end, token_end, previous.content_end, closed=bool(outside) or line.end > line.content_end)
            previous = line
        return BlockSpan(len(self.text), token_end, len(self.text))

    def indented_may_start(self, index: int) -> bool:
        """Allow code after a blank or a confirmed non-paragraph block."""
        if index == 0 or self.blank(index - 1):
            return True
        previous = self.lines[index - 1]
        value = self.projected_line(index - 1)
        return bool(
            previous.start in self.closed_fence_lines
            or previous.start in self.closed_html_lines
            or COMPILED_ATX_START_REGEX.match(value) is not None
            or COMPILED_DOCUMENT_BREAK_REGEX.fullmatch(value) is not None
            or (index > 1 and not self.blank(index - 2) and COMPILED_SETEXT_REGEX.fullmatch(value) is not None)
            or (value.startswith("__MDFLOW_CODE_BLOCK_") and value.endswith("__"))
        )

    def reference_prefix(self, start: int) -> int | None:
        """Read the bounded single-line label prefix of a reference definition."""
        index = self.by_start.get(start)
        if index is None:
            return None
        line = self.lines[index]
        if self.container_steps[index] and not self.indented_may_start(index) and not self.paragraph_interrupts(index):
            return None
        content_start = self.content_starts[index]
        match = COMPILED_REFERENCE_PREFIX_REGEX.match(self.text[content_start : line.content_end])
        if match is None or len(match.group(1)) > 999 or not match.group(1).strip(" \t"):
            return None
        return content_start + match.end()

    def reference_space(self, start: int, origin: int) -> int | None:
        """Skip reference padding through matching container continuation prefixes."""
        steps = self.container_steps[self.by_start[self.line_at(origin).start]]
        at = start
        while at < len(self.text):
            index = self.by_start.get(at)
            if index is not None and at > origin:
                line = self.lines[index]
                content = container_content_start(self.text[at : line.content_end], steps)
                if self.blank(index):
                    return None
                if content is None:
                    value = self.projected_line(index)
                    if self.paragraph_interrupts(index) or self.inline_block_interrupts(index) or fence_opening(value) is not None or COMPILED_ATX_START_REGEX.match(value) is not None:
                        return None
                    content = 0  # A definition permits a lazy paragraph continuation.
                at += content
            if at >= len(self.text) or self.text[at] not in " \t\r\n":
                break
            at += 1
        return at

    def reference_has_blank(self, start: int, end: int) -> bool:
        """Test only whole intervening physical lines after container projection."""
        first = self.by_start[self.line_at(start).start]
        last = self.by_start[self.line_at(end).start]
        return any(self.blank(index) for index in range(first + 1, last))

    def interaction_limit(self, start: int, marker_end: Callable[[int], int | None], *, final: bool = True) -> tuple[int, bool]:
        """Stop incomplete document controls at a blank outside opaque markers."""
        at = start
        while at < len(self.text):
            index = self.by_start.get(at)
            if index is not None and at > start and (final or self.lines[index].end > self.lines[index].content_end):
                value = self.projected_line(index)
                if (
                    self.blank(index)
                    or fence_opening(value) is not None
                    or COMPILED_ATX_START_REGEX.match(value) is not None
                    or self.inline_block_interrupts(index)
                    or self.paragraph_interrupts(index)
                ):
                    return at, False
            if self.text.startswith("{{", at):
                end = marker_end(at)
                if end is None:
                    return len(self.text), False
                at = end
            elif self.text[at] == "\\" and at + 1 < len(self.text) and self.text[at + 1] in "|/.]":
                at += 2
            elif self.text[at] == "]":
                return at, True
            else:
                at += 1
        return len(self.text), False

    def _container_paragraphs(self) -> set[int]:
        """Keep same-container and lazy continuation lines in one paragraph."""
        boundaries: set[int] = set()
        active: tuple[int, ...] = ()
        paragraph = False
        for index, line in enumerate(self.lines):
            value = self.text[line.start : line.content_end]
            if not value.strip(" \t"):
                active, paragraph = (), False
                continue
            content = container_content_start(value, active) if active else 0
            remaining = value[content:] if content is not None else value
            base = active if content is not None else ()
            after, steps = container_opening(remaining)
            if steps and (not paragraph or self._explicit_interrupt(remaining)):
                boundaries.add(index)
                active = base + steps
                remaining = remaining[after:]
            offset = line.start + (content if content is not None else 0)
            if steps and (not paragraph or self._explicit_interrupt(value[(content if content is not None else 0) :])):
                offset += after
            self.content_starts[index] = offset
            self.container_steps[index] = active if content is not None or steps else ()
            if not remaining.strip(" \t"):
                boundaries.add(index)
                paragraph = False
            else:
                paragraph = True
            if fence_opening(remaining) is not None or COMPILED_ATX_START_REGEX.match(remaining) is not None or COMPILED_DOCUMENT_BREAK_REGEX.fullmatch(remaining) is not None:
                paragraph = False
        return boundaries

    @staticmethod
    def _explicit_interrupt(value: str) -> bool:
        at = 0
        while at < min(3, len(value)) and value[at] == " ":
            at += 1
        if at < len(value) and value[at] == ">":
            return True
        marker = COMPILED_CONTAINER_LIST_REGEX.match(value, at)
        if marker is None or (value[at].isdigit() and marker.group() not in ("1.", "1)")):
            return False
        return bool(value[marker.end() :].strip(" \t"))

    def paragraph_interrupts(self, index: int) -> bool:
        """Report a new quote/list paragraph without breaking its own inline spans."""
        return index in self.container_paragraphs

    def inline_block_interrupts(self, index: int) -> bool:
        """Report confirmed thematic and ordinary-HTML paragraph interruptions."""
        value = self.projected_line(index)
        tag = COMPILED_DOCUMENT_TAG_REGEX.match(value)
        return COMPILED_DOCUMENT_BREAK_REGEX.fullmatch(value) is not None or COMPILED_SETEXT_REGEX.fullmatch(value) is not None or (tag is not None and tag.group(1).lower() in HTML_BLOCK_TAGS)
