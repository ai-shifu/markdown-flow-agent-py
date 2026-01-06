"""
Variable Parser Module

Provides variable extraction and replacement functionality for MarkdownFlow documents.
"""

import re
from collections.abc import Mapping

from ..constants import (
    COMPILED_BRACE_VARIABLE_REGEX,
    COMPILED_PERCENT_VARIABLE_REGEX,
    OUTPUT_INSTRUCTION_PREFIX,
    OUTPUT_INSTRUCTION_SUFFIX,
    VARIABLE_DEFAULT_VALUE,
)


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
    variables = set()

    # Match %{{...}} format variables using pre-compiled regex
    matches = COMPILED_PERCENT_VARIABLE_REGEX.findall(text)
    for match in matches:
        variables.add(match.strip())

    # Match {{...}} format variables (excluding %) using pre-compiled regex
    matches = COMPILED_BRACE_VARIABLE_REGEX.findall(text)
    for match in matches:
        variables.add(match.strip())

    return sorted(list(variables))


def is_inside_preserve_tag(text: str, pos: int) -> bool:
    """
    Check if the given position is inside a <preserve_or_translate> tag.

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

    # Convert Mapping to dict for modification, or initialize as empty dict
    if variables:
        # Create a mutable copy
        variables_dict = dict(variables)
        # Check each variable for null or empty values, assign "UNKNOWN" if so
        for key, value in variables_dict.items():
            if value is None or value == "" or (isinstance(value, list) and not value):
                variables_dict[key] = VARIABLE_DEFAULT_VALUE
    else:
        variables_dict = {}

    # Find all {{variable}} format variable references
    variable_pattern = r"\{\{([^{}]+)\}\}"
    matches = re.findall(variable_pattern, text)

    # Assign "UNKNOWN" to undefined variables
    for var_name in matches:
        var_name = var_name.strip()
        if var_name not in variables_dict:
            variables_dict[var_name] = "UNKNOWN"

    # Use updated replacement logic, preserve %{{var_name}} format variables
    result = text
    for var_name, var_value in variables_dict.items():
        # Convert value to string based on type
        if isinstance(var_value, list):
            # Multiple values - join with comma
            value_str = ", ".join(str(v) for v in var_value if v is not None and str(v).strip())
            if not value_str:
                value_str = VARIABLE_DEFAULT_VALUE
        else:
            value_str = str(var_value) if var_value is not None else VARIABLE_DEFAULT_VALUE

        # Find all matches of {{var_name}} (not %{{var_name}})
        # Use negative lookbehind assertion to exclude %{{var_name}} format
        pattern = f"(?<!%){{{{{re.escape(var_name)}}}}}"

        # Replace each match individually, checking if it's inside a preserve tag
        # Use default parameters to capture loop variables (fixes B023)
        def replace_match(match, _value_str=value_str, _result=result, _add_quotes=add_quotes):
            start = match.start()

            # If add_quotes is False, never add quotes (for preserved content blocks)
            if not _add_quotes:
                return _value_str

            # Check if this match is inside a preserve tag
            if is_inside_preserve_tag(_result, start):
                # Inside preserve tag - no triple quotes
                return _value_str
            # Normal variable - add triple quotes
            return f'"""{_value_str}"""'

        result = re.sub(pattern, replace_match, result)

    return result
