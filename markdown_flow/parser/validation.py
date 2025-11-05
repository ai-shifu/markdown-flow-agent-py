"""
Validation Parser Module

Provides validation template generation and response parsing for user input validation.
"""

import json
from typing import Any

from ..constants import (
    CONTEXT_BUTTON_OPTIONS_TEMPLATE,
    CONTEXT_CONVERSATION_TEMPLATE,
    CONTEXT_QUESTION_MARKER,
    CONTEXT_QUESTION_TEMPLATE,
    SMART_VALIDATION_TEMPLATE,
    VALIDATION_ILLEGAL_DEFAULT_REASON,
    VALIDATION_RESPONSE_ILLEGAL,
    VALIDATION_RESPONSE_OK,
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

    Args:
        target_variable: Target variable name
        context: Context message list with role and content fields
        interaction_question: Question text from interaction block
        buttons: Button options list with display and value fields

    Returns:
        Generated validation template
    """
    # Build context information
    context_info = ""
    if interaction_question or context or buttons:
        context_parts = []

        # Add question information (most important, put first)
        if interaction_question:
            context_parts.append(CONTEXT_QUESTION_TEMPLATE.format(question=interaction_question))

        # Add button options information
        if buttons:
            button_displays = [btn.get("display", "") for btn in buttons if btn.get("display")]
            if button_displays:
                button_options_str = ", ".join(button_displays)
                button_info = CONTEXT_BUTTON_OPTIONS_TEMPLATE.format(button_options=button_options_str)
                context_parts.append(button_info)

        # Add conversation context
        if context:
            for msg in context:
                if msg.get("role") == "assistant" and CONTEXT_QUESTION_MARKER not in msg.get("content", ""):
                    # Other assistant messages as context (exclude extracted questions)
                    context_parts.append(CONTEXT_CONVERSATION_TEMPLATE.format(content=msg.get("content", "")))

        if context_parts:
            context_info = "\n\n".join(context_parts)

    # Use template from constants
    # Note: {sys_user_input} will be replaced later in _build_validation_messages
    return SMART_VALIDATION_TEMPLATE.format(
        target_variable=target_variable,
        context_info=context_info,
        sys_user_input="{sys_user_input}",  # Keep placeholder for later replacement
    ).strip()


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
        return {"content": "", "variables": {target_variable: original_input.strip()}}
    return {"content": llm_response, "variables": None}
