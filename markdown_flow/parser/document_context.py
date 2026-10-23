"""Document-stage boundaries without changing the raw variable-marker grammar."""

from collections.abc import Iterator

from ..constants import COMPILED_INLINE_HTML_REGEX
from ..variable_names import VariableMarker, find_interaction_end, find_variable_markers, read_variable_marker
from .code_fence_utils import is_code_fence_end, parse_code_fence_start


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


def read_document_literal_end(text: str, start: int) -> int | None:
    """Read a Markdown literal region; unmatched inline tick runs stop locally."""
    fenced_end = _fenced_code_end(text, start)
    if fenced_end is not None:
        return fenced_end
    if text[start] == "\\":
        return min(start + 2, len(text))
    if text[start] == "<":
        html = COMPILED_INLINE_HTML_REGEX.match(text, start)
        return html.end() if html is not None else None
    if text[start] != "`":
        return None

    opening_end = start + 1
    while opening_end < len(text) and text[opening_end] == "`":
        opening_end += 1
    size = opening_end - start
    at = opening_end
    while at < len(text):
        if text[at] == "\n":
            line_end = text.find("\n", at + 1)
            line = text[at + 1 : line_end if line_end >= 0 else len(text)]
            # Inline code cannot absorb a later fenced block or a new paragraph.
            if not line.strip() or parse_code_fence_start(line) is not None:
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
    while at < len(text):
        if at > interaction_until:
            literal_end = read_document_literal_end(text, at)
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
            for marker in find_variable_markers(text[start:end]):
                yield VariableMarker(start + marker.start, start + marker.end, marker.raw_name, marker.name)
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
    while at < len(text):
        literal_end = read_document_literal_end(text, at)
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
