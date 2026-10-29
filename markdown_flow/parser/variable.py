"""
Variable Parser Module

Provides variable extraction and replacement functionality for MarkdownFlow documents.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from ..constants import (
    COMPILED_LAYER2_VARIABLE_REGEX,
    OUTPUT_INSTRUCTION_PREFIX,
    OUTPUT_INSTRUCTION_SUFFIX,
    VARIABLE_DEFAULT_VALUE,
)
from .document_context import find_document_interaction_spans, find_document_variable_markers


class _PreserveTagState:
    """Track real output tags without interpreting the contents of opaque markers."""

    def __init__(self):
        self.inside = False
        self._tail = ""

    def feed(self, text: str) -> None:
        combined = self._tail + text
        opening = combined.rfind(OUTPUT_INSTRUCTION_PREFIX)
        closing = combined.rfind(OUTPUT_INSTRUCTION_SUFFIX)
        if opening >= 0 or closing >= 0:
            self.inside = opening > closing
        # Retain incomplete tags that may continue across replacement boundaries.
        self._tail = combined[-(max(len(OUTPUT_INSTRUCTION_PREFIX), len(OUTPUT_INSTRUCTION_SUFFIX)) - 1) :]

    def skip_marker(self) -> None:
        self._tail = ""


@dataclass
class _ReplacementSegment:
    """Keep original markers distinct from literal text and already rendered values."""

    text: str
    variable_name: str | None = None
    opaque: bool = False


def extract_variables_from_text(text: str) -> list[str]:
    """
    Extract all variable names from text.

    Recognizes two variable formats:
    - %{{variable_name}} format (preserved variables)
    - {{variable_name}} format (replaceable variables)

    Args:
        text: Text content to analyze

    Returns:
        Sorted list of unique variable names
    """
    return sorted({marker.name for marker in find_document_variable_markers(text) if marker.name is not None})


def is_inside_preserve_tag(text: str, pos: int) -> bool:
    """Read structural preserve state before pos, excluding all complete markers."""
    state = _PreserveTagState()
    at = 0
    for marker in find_document_variable_markers(text):
        if marker.start >= pos:
            break
        state.feed(text[at : marker.start])
        if marker.end > pos:
            return state.inside
        state.skip_marker()
        at = marker.end
    state.feed(text[at:pos])
    return state.inside


def replace_variables_in_text(
    text: str,
    variables: Mapping[str, str | list[str]] | None = None,
    add_quotes: bool = True,
    *,
    _preserve_interaction_bindings: bool = True,
) -> str:
    """
    Replace variables in text, undefined or empty variables are auto-assigned "UNKNOWN".

    Args:
        text: Text containing variables
        variables: Variable name to value mapping (accepts dict or any Mapping type)
        add_quotes: Whether to add triple quotes around replaced values (default: True).
                   Set to False for preserved content blocks where quotes should not be added.

    Returns:
        Text with variables replaced
    """
    if not text or not isinstance(text, str):
        return text or ""
    if "{{" not in text:
        return text

    # A leading marker binds the answer in either spelling. Preserve only that
    # occurrence; references in the question body or outside controls still read
    # memory. The document scanner excludes literal examples and escaped controls.
    bindings = set()
    # Already classified content producers disable binding discovery: their
    # slices may no longer include the owning definition or native HTML sibling.
    interactions = find_document_interaction_spans(text) if _preserve_interaction_bindings else ()
    for start, end in interactions:
        body_start = start + 2
        binding = COMPILED_LAYER2_VARIABLE_REGEX.match(text[body_start : end - 1])
        if binding is not None:
            bindings.add(body_start + binding.start(1) - len("{{"))

    values = dict(variables or {})
    segments: list[_ReplacementSegment] = []
    at = 0
    for marker in find_document_variable_markers(text):
        segments.append(_ReplacementSegment(text[at : marker.start]))
        assignment = marker.start in bindings or (marker.start and text[marker.start - 1] == "%")
        name = marker.name if not assignment else None
        segments.append(_ReplacementSegment(text[marker.start : marker.end], name, opaque=True))
        if name is not None:
            values.setdefault(name, VARIABLE_DEFAULT_VALUE)
        at = marker.end
    segments.append(_ReplacementSegment(text[at:]))

    # As in the historical per-variable replacement, every occurrence of one
    # key sees the same pre-batch state. Only the next key sees emitted values.
    for name, var_value in values.items():
        if isinstance(var_value, list):
            value_str = ", ".join(str(v) for v in var_value if v is not None and str(v).strip())
            if not value_str:
                value_str = VARIABLE_DEFAULT_VALUE
        else:
            value_str = str(var_value) if var_value not in (None, "") else VARIABLE_DEFAULT_VALUE
        preserve = _PreserveTagState()
        for segment in segments:
            if not segment.opaque:
                preserve.feed(segment.text)
                continue
            if segment.variable_name == name:
                segment.text = f'"""{value_str}"""' if add_quotes and not preserve.inside else value_str
                segment.variable_name = None
                segment.opaque = False
            # Read the original marker in this batch, never its new value.
            preserve.skip_marker()
    return "".join(segment.text for segment in segments)
