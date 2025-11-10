"""
Validation Parser Module

Provides validation template generation and response parsing for user input validation.
"""

import json
from typing import Any

from ..constants import (
    VALIDATION_ILLEGAL_DEFAULT_REASON,
    VALIDATION_RESPONSE_ILLEGAL,
    VALIDATION_RESPONSE_OK,
    VALIDATION_TASK_TEMPLATE,
)
from .json_parser import parse_json_response


def generate_smart_validation_template(
    target_variable: str,
    context: list[dict[str, Any]] | None = None,
    interaction_question: str | None = None,
    buttons: list[dict[str, str]] | None = None,
) -> str:
    """
    Generate smart validation template based on context and question.

    DEPRECATED: This function is no longer used internally.
    Use _build_validation_messages() in MarkdownFlow class instead.

    Args:
        target_variable: Target variable name
        context: Context message list with role and content fields
        interaction_question: Question text from interaction block
        buttons: Button options list with display and value fields

    Returns:
        Generated validation template (for backward compatibility)
    """
    # For backward compatibility, return a simple template
    # This function is no longer used in the core validation flow
    template = VALIDATION_TASK_TEMPLATE.replace("{target_variable}", target_variable)
    template += "\n\n# 用户回答\n{sys_user_input}"
    return template.strip()


def parse_validation_response(llm_response: str, original_input: str, target_variable: str) -> dict[str, Any]:
    """
    Parse LLM validation response, returning standard format.

    Supports JSON format and natural language text responses.

    Args:
        llm_response: LLM's raw response
        original_input: User's original input
        target_variable: Target variable name

    Returns:
        Standardized parsing result with content and variables fields
    """
    try:
        # Try to parse JSON response
        parsed_response = parse_json_response(llm_response)

        if isinstance(parsed_response, dict):
            result = parsed_response.get("result", "").lower()

            if result == VALIDATION_RESPONSE_OK:
                # Validation successful
                parse_vars = parsed_response.get("parse_vars", {})
                if target_variable not in parse_vars:
                    parse_vars[target_variable] = original_input.strip()

                # Ensure the variable value is in list format (user_input format)
                if target_variable in parse_vars and not isinstance(parse_vars[target_variable], list):
                    parse_vars[target_variable] = [parse_vars[target_variable]]

                return {"content": "", "variables": parse_vars}

            if result == VALIDATION_RESPONSE_ILLEGAL:
                # Validation failed
                reason = parsed_response.get("reason", VALIDATION_ILLEGAL_DEFAULT_REASON)
                return {"content": reason, "variables": None}

    except (json.JSONDecodeError, ValueError, KeyError):
        # JSON parsing failed, fallback to text mode
        pass

    # Text response parsing (fallback processing)
    response_lower = llm_response.lower()

    # Check against standard response format
    if "ok" in response_lower or "valid" in response_lower:
        # Return in list format to match user_input format
        return {"content": "", "variables": {target_variable: [original_input.strip()]}}
    return {"content": llm_response, "variables": None}
