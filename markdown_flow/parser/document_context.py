"""Document-stage boundaries without changing the raw variable-marker grammar."""

from collections.abc import Iterator
from string import punctuation

from ..constants import (
    COMPILED_ATX_START_REGEX,
    COMPILED_BLANK_LINE_REGEX,
    COMPILED_DOLLAR_RUN_REGEX,
    COMPILED_INDENTED_CODE_REGEX,
    COMPILED_INLINE_HTML_REGEX,
    COMPILED_RAW_HTML_END_REGEX,
    COMPILED_RAW_HTML_START_REGEX,
)
from ..variable_names import VariableMarker, find_interaction_end, find_variable_markers, read_variable_marker
from .code_fence_utils import is_code_fence_end, parse_code_fence_start


_HTML_TERMINATORS = (("<!--", "-->"), ("<?", "?>"), ("<![CDATA[", "]]>"))


def document_html_ends(text: str) -> dict[str, int]:
    """Index possible native HTML closers once for a document scan."""
    return {ending: text.rfind(ending) for ending in (">", *(closing for _, closing in _HTML_TERMINATORS))}


def _html_can_close(text: str, start: int, last_ends: dict[str, int]) -> bool:
    if last_ends[">"] < start:
        return False
    for opening, closing in _HTML_TERMINATORS:
        if text.startswith(opening, start):
            return last_ends[closing] >= start + len(opening)
    return True


def _fenced_code_end(text: str, start: int) -> int | None:
    if start and text[start - 1] != "\n":
        return None
    line_end = text.find("\n", start)
    line_end = line_end if line_end >= 0 else len(text)
    fence = parse_code_fence_start(text[start:line_end])
    if fence is None:
        return None
    at = line_end + 1
    while at < len(text):
        end = text.find("\n", at)
        end = end if end >= 0 else len(text)
        if is_code_fence_end(text[at:end], fence):
            return end
        at = end + 1
    return len(text)


def _indented_code_end(text: str, start: int) -> int | None:
    if start and text[start - 1] != "\n":
        return None
    if start and text[text.rfind("\n", 0, start - 1) + 1 : start - 1].strip(" \t\r"):
        return None
    if COMPILED_INDENTED_CODE_REGEX.match(text, start) is None:
        return None
    at, last_content_end = start, start
    while at < len(text):
        end = text.find("\n", at)
        end = end if end >= 0 else len(text)
        if text[at:end].strip(" \t\r"):
            if COMPILED_INDENTED_CODE_REGEX.match(text, at) is None:
                break
            last_content_end = end
        at = end + 1
    return last_content_end if last_content_end > start else None


def _raw_html_opening(text: str, start: int, last_html_ends: dict[str, int]) -> tuple[str, int] | None:
    if start and text[start - 1] != "\n":
        return None
    opening = COMPILED_RAW_HTML_START_REGEX.match(text, start)
    if opening is None:
        return None
    tag_start = text.find("<", start, opening.end())
    if not _html_can_close(text, tag_start, last_html_ends):
        return None
    token = COMPILED_INLINE_HTML_REGEX.match(text, tag_start)
    return (opening.group(1).lower(), token.end()) if token is not None else None


def _raw_html_bounds(text: str, start: int, last_html_ends: dict[str, int] | None = None) -> tuple[int, int] | None:
    opening = _raw_html_opening(text, start, last_html_ends if last_html_ends is not None else document_html_ends(text))
    if opening is None:
        return None
    name, opening_end = opening
    closing = COMPILED_RAW_HTML_END_REGEX[name].search(text, opening_end)
    if closing is None:
        return opening_end, len(text)
    line_end = text.find("\n", closing.end())
    line_end = line_end if line_end >= 0 else len(text)
    if line_end > closing.end() and text[line_end - 1] == "\r":
        line_end -= 1
    return opening_end, line_end


def literal_variable_markers(text: str, start: int, end: int) -> Iterator[VariableMarker]:
    """Keep opening attributes and raw HTML bodies as separate local examples."""
    bounds = _raw_html_bounds(text, start)
    boundaries = (start, bounds[0], end) if bounds is not None else (start, end)
    for left, right in zip(boundaries, boundaries[1:], strict=False):
        for marker in find_variable_markers(text[left:right]):
            yield VariableMarker(left + marker.start, left + marker.end, marker.raw_name, marker.name)


def read_link_resource_end(text: str, start: int) -> int | None:
    """Read a complete inline-link resource, without claiming an unfinished one."""
    at = start + 1

    def skip_space(cursor: int) -> int | None:
        beginning = cursor
        while cursor < len(text) and text[cursor] in " \t\r\n":
            cursor += 1
        return None if COMPILED_BLANK_LINE_REGEX.search(text, beginning, cursor) else cursor

    at = skip_space(at)
    if at is None or at >= len(text):
        return None
    if text[at] == "<":
        at += 1
        while at < len(text):
            if text[at] == "\\" and at + 1 < len(text) and text[at + 1] in punctuation:
                at += 2
            elif text[at] == ">":
                at += 1
                break
            elif text[at] in "<\r\n":
                return None
            else:
                at += 1
        else:
            return None
    else:
        depth = 0
        while at < len(text):
            character = text[at]
            if character == "\\" and at + 1 < len(text) and text[at + 1] in punctuation:
                at += 2
                continue
            if character in " \t\r\n" or (character == ")" and depth == 0):
                break
            if character == "(":
                depth += 1
                if depth > 32:
                    return None
            elif character == ")":
                depth -= 1
            elif ord(character) < 32:
                return None
            at += 1
        if depth:
            return None
    destination_end = at
    at = skip_space(at)
    if at is None or at >= len(text):
        return None
    if text[at] == ")":
        return at + 1
    if at == destination_end or text[at] not in "\"'(":
        return None
    closing = ")" if text[at] == "(" else text[at]
    at += 1
    title_start = at
    while at < len(text):
        if text[at] == "\\" and at + 1 < len(text) and text[at + 1] in punctuation:
            at += 2
        elif text[at] == closing:
            if COMPILED_BLANK_LINE_REGEX.search(text, title_start, at) is not None:
                return None
            at = skip_space(at + 1)
            return at + 1 if at is not None and at < len(text) and text[at] == ")" else None
        else:
            at += 1
    return None


def _math_spans(text: str, last_html_ends: dict[str, int]) -> dict[int, int]:
    """Index equal-width math delimiters once, bounded by paragraphs and blocks."""
    breaks: list[tuple[int, int]] = []
    line_start = 0
    for line in text.splitlines(keepends=True):
        opening = _raw_html_opening(text, line_start, last_html_ends)
        if not line.strip(" \t\r\n") or parse_code_fence_start(line.rstrip("\r\n")) is not None or opening is not None:
            boundary_end = opening[1] if opening is not None else line_start + len(line.rstrip("\r\n"))
            breaks.append((line_start, boundary_end))
        line_start += len(line)
    for heading in COMPILED_ATX_START_REGEX.finditer(text):
        line_end = text.find("\n", heading.start())
        line_end = line_end if line_end >= 0 else len(text)
        breaks.extend(((heading.start(), heading.start()), (line_end, line_end)))
    breaks.sort()
    spans: dict[int, int] = {}
    next_run: dict[int, tuple[int, int]] = {}
    boundary_index = len(breaks) - 1
    for run in reversed(list(COMPILED_DOLLAR_RUN_REGEX.finditer(text))):
        while boundary_index >= 0 and breaks[boundary_index][0] >= run.end():
            next_run.clear()
            boundary_index -= 1
        if boundary_index >= 0 and breaks[boundary_index][1] > run.start():
            next_run.clear()
            boundary_index -= 1
            continue
        start = run.start()
        before = start
        while before and text[before - 1] == "\\":
            before -= 1
        opening_start = start + (start - before) % 2
        width = run.end() - opening_start
        if width and width in next_run:
            spans[opening_start] = next_run[width][1]
        next_run[run.end() - start] = (start, run.end())
    return spans


class DocumentLiteralReader:
    """Carry only document-stage link-label state and reusable delimiter indexes."""

    def __init__(self, text: str):
        self.text = text
        self.last_html_ends = document_html_ends(text)
        self.math_spans = _math_spans(text, self.last_html_ends)
        self.labels: list[tuple[bool, bool]] = []
        self.active_links: set[int] = set()
        self.resource_start = -1
        self.resource_image = False

    def read(self, start: int) -> int | None:
        end = read_document_literal_end(self.text, start, last_html_ends=self.last_html_ends)
        if end is not None:
            return end
        if self.text[start] == "$" and start in self.math_spans:
            return self.math_spans[start]
        if self.text[start] == "(" and start == self.resource_start:
            resource_end = read_link_resource_end(self.text, start)
            if resource_end is not None and not self.resource_image:
                for index in self.active_links:
                    self.labels[index] = (False, False)
                self.active_links.clear()
            return resource_end
        if self.text[start] == "[":
            image = start > 0 and self.text[start - 1] == "!"
            before = start - 1
            while before > 0 and self.text[before - 1] == "\\":
                before -= 1
            image = image and (start - 1 - before) % 2 == 0
            self.labels.append((image, True))
            if not image:
                self.active_links.add(len(self.labels) - 1)
        elif self.text[start] == "]" and self.labels:
            self.active_links.discard(len(self.labels) - 1)
            self.resource_image, active = self.labels.pop()
            self.resource_start = start + 1 if active else -1
        elif self.text[start] == "\n":
            following = self.text.find("\n", start + 1)
            if not self.text[start + 1 : following if following >= 0 else len(self.text)].strip(" \t\r"):
                self.labels.clear()
                self.active_links.clear()
        return None


def read_document_literal_end(text: str, start: int, *, last_html_ends: dict[str, int] | None = None) -> int | None:
    """Read a Markdown literal region; unmatched inline tick runs stop locally."""
    fenced_end = _fenced_code_end(text, start)
    if fenced_end is not None:
        return fenced_end
    indented_end = _indented_code_end(text, start)
    if indented_end is not None:
        return indented_end
    raw_html = _raw_html_bounds(text, start, last_html_ends)
    if raw_html is not None:
        return raw_html[1]
    if text[start] == "\\":
        # Markdown escapes ASCII punctuation, never the following line ending.
        return start + 2 if start + 1 < len(text) and text[start + 1] in punctuation else None
    if text[start] == "<":
        if not _html_can_close(text, start, last_html_ends if last_html_ends is not None else document_html_ends(text)):
            return None
        html = COMPILED_INLINE_HTML_REGEX.match(text, start)
        return html.end() if html is not None else None
    if text[start] != "`":
        return None

    opening_end = start + 1
    while opening_end < len(text) and text[opening_end] == "`":
        opening_end += 1
    size = opening_end - start
    opening_heading = COMPILED_ATX_START_REGEX.match(text, text.rfind("\n", 0, start) + 1) is not None
    at = opening_end
    while at < len(text):
        if text[at] == "\n":
            line_end = text.find("\n", at + 1)
            line = text[at + 1 : line_end if line_end >= 0 else len(text)]
            # Inline code cannot absorb a later fenced block or a new paragraph.
            if (
                opening_heading
                or COMPILED_ATX_START_REGEX.match(text, at + 1) is not None
                or not line.strip()
                or parse_code_fence_start(line) is not None
                or _raw_html_bounds(text, at + 1) is not None
            ):
                break
        if text[at] == "`":
            end = at + 1
            while end < len(text) and text[end] == "`":
                end += 1
            if end - at == size:
                return end
            at = end
        else:
            at += 1
    # An unmatched run is literal punctuation; its following braces stay active.
    return opening_end


def _document_units(text: str) -> Iterator[tuple[int, int, bool]]:
    """Yield literal markup and raw-marker regions, keeping interaction bodies raw."""
    at = 0
    interaction_until = -1
    reader = DocumentLiteralReader(text)
    while at < len(text):
        if at > interaction_until:
            literal_end = reader.read(at)
            if literal_end is not None:
                yield at, literal_end, True
                at = literal_end
                continue
            if text.startswith("?[", at):
                end = find_interaction_end(text, at + 2)
                interaction_until = end if end >= 0 else len(text)
        if text.startswith("{{", at):
            marker = read_variable_marker(text, at)
            end = marker.end if marker is not None else len(text)
            yield at, end, False
            at = end
        else:
            at += 1


def find_document_variable_markers(text: str) -> Iterator[VariableMarker]:
    """Collect complete examples inside markup, without letting them cross its edge."""
    for start, end, literal in _document_units(text):
        if literal:
            if text[start] == "\\":
                continue
            yield from literal_variable_markers(text, start, end)
        else:
            marker = read_variable_marker(text, start)
            if marker is not None:
                yield marker


def find_document_protected_spans(text: str) -> Iterator[tuple[int, int]]:
    """Keep document separators outside marker names and already-owned markup."""
    for start, end, _ in _document_units(text):
        yield start, end


def find_document_interaction_spans(text: str) -> Iterator[tuple[int, int]]:
    """Find controls outside markup while retaining raw ownership inside controls."""
    at = 0
    reader = DocumentLiteralReader(text)
    while at < len(text):
        literal_end = reader.read(at)
        if literal_end is not None:
            at = literal_end
        elif text.startswith("{{", at):
            marker = read_variable_marker(text, at)
            if marker is None:
                return
            at = marker.end
        elif text.startswith("?[", at):
            end = find_interaction_end(text, at + 2)
            if end < 0:
                return
            if text[end + 1 : end + 2] != "(":
                yield at, end + 1
            at = end + 1
        else:
            at += 1
