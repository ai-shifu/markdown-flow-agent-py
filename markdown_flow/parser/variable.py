"""
Variable Parser Module

Provides variable extraction and replacement functionality for MarkdownFlow documents.
"""

from collections.abc import Mapping

from ..constants import (
    OUTPUT_INSTRUCTION_PREFIX,
    OUTPUT_INSTRUCTION_SUFFIX,
    VARIABLE_DEFAULT_VALUE,
)
from ..variable_names import find_variable_markers


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
    return sorted({marker.name for marker in find_variable_markers(text) if marker.name is not None})


def is_inside_preserve_tag(text: str, pos: int) -> bool:
    """Read structural preserve state before pos, excluding all complete markers."""
    state = _PreserveTagState()
    at = 0
    for marker in find_variable_markers(text):
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

    values = variables or {}
    out: list[str] = []
    preserve = _PreserveTagState()
    at = 0
    for marker in find_variable_markers(text):
        literal = text[at : marker.start]
        out.append(literal)
        preserve.feed(literal)
        at = marker.end
        if marker.name is None or (marker.start and text[marker.start - 1] == "%"):
            out.append(text[marker.start : marker.end])
            preserve.skip_marker()
            continue
        var_value = values.get(marker.name, VARIABLE_DEFAULT_VALUE)
        if isinstance(var_value, list):
            value_str = ", ".join(str(v) for v in var_value if v is not None and str(v).strip())
            if not value_str:
                value_str = VARIABLE_DEFAULT_VALUE
        else:
            value_str = str(var_value) if var_value not in (None, "") else VARIABLE_DEFAULT_VALUE
        rendered = f'"""{value_str}"""' if add_quotes and not preserve.inside else value_str
        out.append(rendered)
        # Values remain literal and are never substituted recursively; real tags
        # they emit still affect later references, as in the historical renderer.
        preserve.feed(rendered)
    out.append(text[at:])
    return "".join(out)
