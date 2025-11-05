"""
Variable Parser Module

Provides variable extraction and replacement functionality for MarkdownFlow documents.
"""

import re

from ..constants import (
    COMPILED_BRACE_VARIABLE_REGEX,
    COMPILED_PERCENT_VARIABLE_REGEX,
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


def replace_variables_in_text(text: str, variables: dict[str, str | list[str]]) -> str:
    """
    Replace variables in text, undefined or empty variables are auto-assigned "UNKNOWN".

    Args:
        text: Text containing variables
        variables: Variable name to value mapping

    Returns:
        Text with variables replaced
    """
    if not text or not isinstance(text, str):
        return text or ""

    # Check each variable for null or empty values, assign "UNKNOWN" if so
    if variables:
        for key, value in variables.items():
            if value is None or value == "" or (isinstance(value, list) and not value):
                variables[key] = VARIABLE_DEFAULT_VALUE

    # Initialize variables as empty dict (if None)
    if not variables:
        variables = {}

    # Find all {{variable}} format variable references
    variable_pattern = r"\{\{([^{}]+)\}\}"
    matches = re.findall(variable_pattern, text)

    # Assign "UNKNOWN" to undefined variables
    for var_name in matches:
        var_name = var_name.strip()
        if var_name not in variables:
            variables[var_name] = "UNKNOWN"

    # Use updated replacement logic, preserve %{{var_name}} format variables
    result = text
    for var_name, var_value in variables.items():
        # Convert value to string based on type
        if isinstance(var_value, list):
            # Multiple values - join with comma
            value_str = ", ".join(str(v) for v in var_value if v is not None and str(v).strip())
            if not value_str:
                value_str = VARIABLE_DEFAULT_VALUE
        else:
            value_str = str(var_value) if var_value is not None else VARIABLE_DEFAULT_VALUE

        # Use negative lookbehind assertion to exclude %{{var_name}} format
        pattern = f"(?<!%){{{{{re.escape(var_name)}}}}}"
        result = re.sub(pattern, value_str, result)

    return result
