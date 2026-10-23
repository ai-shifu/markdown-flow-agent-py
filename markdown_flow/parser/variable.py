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
    """
    Check if the given position is inside a <原样输出> tag.

    Detection logic:
    1. Find the most recent opening tag before pos
    2. Check if there's a closing tag between the opening tag and pos
    3. If closing tag exists between them, pos is NOT inside
    4. If no closing tag between them, pos IS inside

    Args:
        text: Full text content
        pos: Position to check (variable start position)

    Returns:
        True if position is inside preserve tag, False otherwise
    """
    # Find the most recent opening tag before pos
    last_open_index = text.rfind(OUTPUT_INSTRUCTION_PREFIX, 0, pos)

    # If no opening tag found, definitely not inside
    if last_open_index == -1:
        return False

    # Find closing tag between the opening tag and pos
    # Search from position after the opening tag to pos
    close_between = text.find(OUTPUT_INSTRUCTION_SUFFIX, last_open_index + len(OUTPUT_INSTRUCTION_PREFIX), pos)

    # If there's a closing tag between opening tag and pos,
    # it means the opening tag is already closed, so pos is NOT inside
    # Otherwise, pos IS inside (whether or not there's a closing tag after pos doesn't matter)
    return close_between == -1


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
    at = 0
    for marker in find_variable_markers(text):
        out.append(text[at : marker.start])
        at = marker.end
        if marker.name is None or (marker.start and text[marker.start - 1] == "%"):
            out.append(text[marker.start : marker.end])
            continue
        var_value = values.get(marker.name, VARIABLE_DEFAULT_VALUE)
        if isinstance(var_value, list):
            value_str = ", ".join(str(v) for v in var_value if v is not None and str(v).strip())
            if not value_str:
                value_str = VARIABLE_DEFAULT_VALUE
        else:
            value_str = str(var_value) if var_value not in (None, "") else VARIABLE_DEFAULT_VALUE
        out.append(f'"""{value_str}"""' if add_quotes and not is_inside_preserve_tag(text, marker.start) else value_str)
    out.append(text[at:])
    return "".join(out)
