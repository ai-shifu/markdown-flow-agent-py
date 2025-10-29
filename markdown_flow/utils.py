"""
Markdown-Flow Utility Functions

Collection of utility functions for document parsing, variable extraction, and text processing.
"""

import json
import re
from enum import Enum
from typing import Any

from .constants import (
    COMPILED_BRACE_VARIABLE_REGEX,
    COMPILED_INLINE_PRESERVE_REGEX,
    COMPILED_INTERACTION_REGEX,
    COMPILED_LAYER1_INTERACTION_REGEX,
    COMPILED_LAYER2_VARIABLE_REGEX,
    COMPILED_LAYER3_ELLIPSIS_REGEX,
    COMPILED_PERCENT_VARIABLE_REGEX,
    COMPILED_PRESERVE_FENCE_REGEX,
    COMPILED_SINGLE_PIPE_SPLIT_REGEX,
    CONTEXT_BUTTON_OPTIONS_TEMPLATE,
    CONTEXT_CONVERSATION_TEMPLATE,
    CONTEXT_QUESTION_MARKER,
    CONTEXT_QUESTION_TEMPLATE,
    JSON_PARSE_ERROR,
    OUTPUT_INSTRUCTION_PREFIX,
    OUTPUT_INSTRUCTION_SUFFIX,
    SMART_VALIDATION_TEMPLATE,
    VALIDATION_ILLEGAL_DEFAULT_REASON,
    VALIDATION_RESPONSE_ILLEGAL,
    VALIDATION_RESPONSE_OK,
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


def is_preserved_content_block(content: str) -> bool:
    """
    Check if content is completely preserved content block.

    Preserved blocks are entirely wrapped by markers with no external content.
    Supports inline (===content===), multiline (!=== ... !===) formats, and mixed formats.

    Args:
        content: Content to check

    Returns:
        True if content is fully wrapped by preserved markers
    """
    content = content.strip()
    if not content:
        return False

    lines = content.split("\n")

    # Use state machine to validate that all non-empty content is preserved
    state = "OUTSIDE"  # States: OUTSIDE, INSIDE
    has_preserve_content = False

    for line in lines:
        stripped_line = line.strip()

        # Check if this line is a fence marker (!===)
        if COMPILED_PRESERVE_FENCE_REGEX.match(stripped_line):
            if state == "OUTSIDE":
                # Enter preserve block
                state = "INSIDE"
                has_preserve_content = True
            elif state == "INSIDE":
                # Exit preserve block
                state = "OUTSIDE"
            # Fence markers themselves are valid preserved content
            continue

        # Non-fence lines
        if stripped_line:  # Non-empty line
            if state == "INSIDE":
                # Inside fence block, this is valid preserved content
                has_preserve_content = True
            else:
                # Outside fence block, check if it's inline format
                match = COMPILED_INLINE_PRESERVE_REGEX.match(stripped_line)
                if match:
                    # Ensure inner content exists and contains no ===
                    inner_content = match.group(1).strip()
                    if inner_content and "===" not in inner_content:
                        # Valid inline format
                        has_preserve_content = True
                    else:
                        # Invalid inline format
                        return False
                else:
                    # Not fence, not inline format -> external content
                    return False

    # Judgment conditions:
    # 1. Must have preserved content
    # 2. Final state must be OUTSIDE (all fence blocks closed)
    return has_preserve_content and state == "OUTSIDE"


def extract_interaction_question(content: str) -> str | None:
    """
    Extract question text from interaction block content.

    Args:
        content: Raw interaction block content

    Returns:
        Question text if found, None otherwise
    """
    # Match interaction format: ?[...] using pre-compiled regex
    match = COMPILED_INTERACTION_REGEX.match(content.strip())
    if not match:
        return None  # type: ignore[unreachable]

    # Extract interaction content (remove ?[ and ])
    interaction_content = match.group(1) if match.groups() else match.group(0)[2:-1]

    # Find ... separator, question text follows
    if "..." in interaction_content:
        # Split and get question part
        parts = interaction_content.split("...", 1)
        if len(parts) > 1:
            return parts[1].strip()

    return None  # type: ignore[unreachable]


class InteractionType(Enum):
    """Interaction input type enumeration."""

    TEXT_ONLY = "text_only"  # Text input only: ?[%{{var}}...question]
    BUTTONS_ONLY = "buttons_only"  # Button selection only: ?[%{{var}} A|B]
    BUTTONS_WITH_TEXT = "buttons_with_text"  # Buttons + text: ?[%{{var}} A|B|...question]
    BUTTONS_MULTI_SELECT = "buttons_multi_select"  # Multi-select buttons: ?[%{{var}} A||B]
    BUTTONS_MULTI_WITH_TEXT = "buttons_multi_with_text"  # Multi-select + text: ?[%{{var}} A||B||...question]
    NON_ASSIGNMENT_BUTTON = "non_assignment_button"  # Display buttons: ?[Continue|Cancel]


class InteractionParser:
    """
    Three-layer interaction parser for ?[] format validation,
    variable detection, and content parsing.
    """

    def __init__(self):
        """Initialize parser."""

    def parse(self, content: str) -> dict[str, Any]:
        """
        Main parsing method.

        Args:
            content: Raw interaction block content

        Returns:
            Standardized parsing result with type, variable, buttons, and question fields
        """
        try:
            # Layer 1: Validate basic format
            inner_content = self._layer1_validate_format(content)
            if inner_content is None:
                return self._create_error_result(f"Invalid interaction format: {content}")

            # Layer 2: Variable detection and pattern classification
            has_variable, variable_name, remaining_content = self._layer2_detect_variable(inner_content)

            # Layer 3: Specific content parsing
            if has_variable:
                assert variable_name is not None, "variable_name should not be None when has_variable is True"
                return self._layer3_parse_variable_interaction(variable_name, remaining_content)
            return self._layer3_parse_display_buttons(inner_content)

        except Exception as e:
            return self._create_error_result(f"Parsing error: {str(e)}")

    def _layer1_validate_format(self, content: str) -> str | None:
        """
        Layer 1: Validate ?[] format and extract content.

        Args:
            content: Raw content

        Returns:
            Extracted bracket content, None if validation fails
        """
        content = content.strip()
        match = COMPILED_LAYER1_INTERACTION_REGEX.search(content)

        if not match:
            return None  # type: ignore[unreachable]

        # Ensure matched content is complete (no other text)
        matched_text = match.group(0)
        if matched_text.strip() != content:
            return None

        return match.group(1)

    def _layer2_detect_variable(self, inner_content: str) -> tuple[bool, str | None, str]:
        """
        Layer 2: Detect variables and classify patterns.

        Args:
            inner_content: Content extracted from layer 1

        Returns:
            Tuple of (has_variable, variable_name, remaining_content)
        """
        match = COMPILED_LAYER2_VARIABLE_REGEX.match(inner_content)

        if not match:
            # No variable, use entire content for display button parsing
            return False, None, inner_content  # type: ignore[unreachable]

        variable_name = match.group(1).strip()
        remaining_content = match.group(2).strip()

        return True, variable_name, remaining_content

    def _layer3_parse_variable_interaction(self, variable_name: str, content: str) -> dict[str, Any]:
        """
        Layer 3: Parse variable interactions (variable assignment type).

        Args:
            variable_name: Variable name
            content: Content after variable

        Returns:
            Parsing result dictionary
        """
        # Detect ... separator
        ellipsis_match = COMPILED_LAYER3_ELLIPSIS_REGEX.match(content)

        if ellipsis_match:
            # Has ... separator
            before_ellipsis = ellipsis_match.group(1).strip()
            question = ellipsis_match.group(2).strip()

            if before_ellipsis:
                # Has prefix content (buttons or single option) + text input
                buttons, is_multi_select = self._parse_buttons(before_ellipsis)
                interaction_type = InteractionType.BUTTONS_MULTI_WITH_TEXT if is_multi_select else InteractionType.BUTTONS_WITH_TEXT
                return {
                    "type": interaction_type,
                    "variable": variable_name,
                    "buttons": buttons,
                    "question": question,
                    "is_multi_select": is_multi_select,
                }
            # Pure text input
            return {
                "type": InteractionType.TEXT_ONLY,
                "variable": variable_name,
                "question": question,
                "is_multi_select": False,
            }
        # No ... separator
        if ("|" in content or "||" in content) and content:  # type: ignore[unreachable]
            # Pure button group
            buttons, is_multi_select = self._parse_buttons(content)
            interaction_type = InteractionType.BUTTONS_MULTI_SELECT if is_multi_select else InteractionType.BUTTONS_ONLY
            return {
                "type": interaction_type,
                "variable": variable_name,
                "buttons": buttons,
                "is_multi_select": is_multi_select,
            }
        if content:  # type: ignore[unreachable]
            # Single button
            button = self._parse_single_button(content)
            return {
                "type": InteractionType.BUTTONS_ONLY,
                "variable": variable_name,
                "buttons": [button],
                "is_multi_select": False,
            }
        # Pure text input (no hint)
        return {
            "type": InteractionType.TEXT_ONLY,
            "variable": variable_name,
            "question": "",
            "is_multi_select": False,
        }

    def _layer3_parse_display_buttons(self, content: str) -> dict[str, Any]:
        """
        Layer 3: Parse display buttons (non-variable assignment type).

        Args:
            content: Content to parse

        Returns:
            Parsing result dictionary
        """
        if not content:
            # Empty content: ?[]
            return {
                "type": InteractionType.NON_ASSIGNMENT_BUTTON,
                "buttons": [{"display": "", "value": ""}],
            }

        if "|" in content:
            # Multiple buttons
            buttons, _ = self._parse_buttons(content)  # Display buttons don't use multi-select
            return {"type": InteractionType.NON_ASSIGNMENT_BUTTON, "buttons": buttons}
        # Single button
        button = self._parse_single_button(content)
        return {"type": InteractionType.NON_ASSIGNMENT_BUTTON, "buttons": [button]}

    def _parse_buttons(self, content: str) -> tuple[list[dict[str, str]], bool]:
        """
        Parse button group with fault tolerance.

        Args:
            content: Button content separated by | or ||

        Returns:
            Tuple of (button list, is_multi_select)
        """
        if not content or not isinstance(content, str):
            return [], False

        _, is_multi_select = self._detect_separator_type(content)

        buttons = []
        try:
            # Use different splitting logic based on separator type
            if is_multi_select:
                # Multi-select mode: split on ||, preserve single |
                button_parts = content.split("||")
            else:
                # Single-select mode: split on single |, but preserve ||
                # Use pre-compiled regex from constants
                button_parts = COMPILED_SINGLE_PIPE_SPLIT_REGEX.split(content)

            for button_text in button_parts:
                button_text = button_text.strip()
                if button_text:
                    button = self._parse_single_button(button_text)
                    buttons.append(button)
        except (TypeError, ValueError):
            # Fallback to treating entire content as single button
            return [{"display": content.strip(), "value": content.strip()}], False

        # For empty content (like just separators), return empty list
        if not buttons and (content.strip() == "||" or content.strip() == "|"):
            return [], is_multi_select

        # Ensure at least one button exists (but only if there's actual content)
        if not buttons and content.strip():
            buttons = [{"display": content.strip(), "value": content.strip()}]

        return buttons, is_multi_select

    def _parse_single_button(self, button_text: str) -> dict[str, str]:
        """
        Parse single button with fault tolerance, supports Button//value format.

        Args:
            button_text: Button text

        Returns:
            Dictionary with display and value keys
        """
        if not button_text or not isinstance(button_text, str):
            return {"display": "", "value": ""}

        button_text = button_text.strip()
        if not button_text:
            return {"display": "", "value": ""}

        try:
            # Detect Button//value format - split only on first //
            if "//" in button_text:
                parts = button_text.split("//", 1)  # Split only on first //
                display = parts[0].strip()
                value = parts[1] if len(parts) > 1 else ""
                # Don't strip value to preserve intentional spacing/formatting
                return {"display": display, "value": value}
        except (ValueError, IndexError):
            # Fallback: use text as both display and value
            pass

        return {"display": button_text, "value": button_text}

    def _detect_separator_type(self, content: str) -> tuple[str, bool]:
        """
        Detect separator type and whether it's multi-select.

        Implements fault tolerance: first separator type encountered determines the behavior.
        Mixed separators are handled by treating the rest as literal text.

        Args:
            content: Button content to analyze

        Returns:
            Tuple of (separator, is_multi_select) where separator is '|' or '||'
        """
        if not content or not isinstance(content, str):
            return "|", False

        # Find first occurrence of separators
        single_pos = content.find("|")
        double_pos = content.find("||")

        # If no separators found
        if single_pos == -1 and double_pos == -1:
            return "|", False

        # If only single separator found
        if double_pos == -1:
            return "|", False

        # If only double separator found
        if single_pos == -1:
            return "||", True

        # Both found - fault tolerance: first occurrence wins
        # This handles mixed cases like "A||B|C" (multi-select) and "A|B||C" (single-select)
        if double_pos <= single_pos:
            return "||", True
        return "|", False

    def _create_error_result(self, error_message: str) -> dict[str, Any]:
        """
        Create error result.

        Args:
            error_message: Error message

        Returns:
            Error result dictionary
        """
        return {"type": None, "error": error_message}  # type: ignore[unreachable]


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


def parse_json_response(response_text: str) -> dict[str, Any]:
    """
    Parse JSON response supporting multiple formats.

    Supports pure JSON strings, ```json code blocks, and mixed text formats.

    Args:
        response_text: Response text to parse

    Returns:
        Parsed dictionary object

    Raises:
        ValueError: When JSON cannot be parsed
    """
    text = response_text.strip()

    # Extract JSON code block
    if "```json" in text:
        start_idx = text.find("```json") + 7
        end_idx = text.find("```", start_idx)
        if end_idx != -1:
            text = text[start_idx:end_idx].strip()
    elif "```" in text:
        start_idx = text.find("```") + 3
        end_idx = text.find("```", start_idx)
        if end_idx != -1:
            text = text[start_idx:end_idx].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract first JSON object
        json_match = re.search(r"\{[^}]+\}", text)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError(JSON_PARSE_ERROR)


def process_output_instructions(content: str) -> tuple[str, bool]:
    """
    Process output instruction markers, converting !=== format to [output] format.

    Uses unified state machine to handle inline (===content===) and multiline (!===...!===) formats.

    Args:
        content: Raw content containing output instructions

    Returns:
        Tuple of (processed_content, has_preserved_content):
        - processed_content: Content with === and !=== markers converted to XML format
        - has_preserved_content: True if content contained preserved markers
    """
    lines = content.split("\n")
    result_lines = []
    i = 0
    has_output_instruction = False

    while i < len(lines):
        line = lines[i]

        # Check if contains preserved markers (inline ===...=== or multiline !===...)
        # Check inline format first: ===content===
        inline_match = re.search(r"===\s*(.+?)\s*===", line)
        if inline_match and line.count("===") == 2 and not line.strip().startswith("!"):
            inner_content = inline_match.group(1).strip()
            # Validate that inner content doesn't contain ===
            if not inner_content or "===" in inner_content:
                result_lines.append(line)
                i += 1
                continue
            # Process inline format
            full_match = inline_match.group(0)

            # Build output instruction - keep inline format on same line
            output_instruction = f"{OUTPUT_INSTRUCTION_PREFIX}{inner_content}{OUTPUT_INSTRUCTION_SUFFIX}"

            # Replace ===...=== part in original line
            processed_line = line.replace(full_match, output_instruction)
            result_lines.append(processed_line)
            has_output_instruction = True
            i += 1

        elif COMPILED_PRESERVE_FENCE_REGEX.match(line.strip()):
            # Multiline format start
            i += 1
            output_content_lines: list[str] = []

            # Collect multiline content
            while i < len(lines):
                current_line = lines[i]
                if COMPILED_PRESERVE_FENCE_REGEX.match(current_line.strip()):
                    # Found end marker, process collected content
                    output_content = "\n".join(output_content_lines).strip()

                    # Special handling for title format (maintain original logic)
                    hash_prefix = ""
                    if output_content.startswith("#"):
                        first_space = output_content.find(" ")
                        first_newline = output_content.find("\n")

                        if first_space != -1 and (first_newline == -1 or first_space < first_newline):
                            hash_prefix = output_content[: first_space + 1]
                            output_content = output_content[first_space + 1 :].strip()
                        elif first_newline != -1:
                            hash_prefix = output_content[: first_newline + 1]
                            output_content = output_content[first_newline + 1 :].strip()

                    # Build output instruction
                    if hash_prefix:
                        result_lines.append(f"{OUTPUT_INSTRUCTION_PREFIX}{hash_prefix}{output_content}{OUTPUT_INSTRUCTION_SUFFIX}")
                    else:
                        result_lines.append(f"{OUTPUT_INSTRUCTION_PREFIX}{output_content}{OUTPUT_INSTRUCTION_SUFFIX}")

                    has_output_instruction = True
                    i += 1
                    break
                # Continue collecting content
                output_content_lines.append(current_line)  # type: ignore[unreachable]
                i += 1
            else:
                # No end marker found, rollback processing
                result_lines.append(lines[i - len(output_content_lines) - 1])
                result_lines.extend(output_content_lines)
        else:
            # Normal line
            result_lines.append(line)  # type: ignore[unreachable]
            i += 1

    # Assemble final content
    processed_content = "\n".join(result_lines)

    # Return both processed content and whether it contains preserved content
    return processed_content, has_output_instruction


def extract_preserved_content(content: str) -> str:
    """
    Extract actual content from preserved content blocks, removing markers.

    Handles inline (===content===) and multiline (!===...!===) formats.

    Args:
        content: Preserved content containing preserved markers

    Returns:
        Actual content with === and !=== markers removed
    """
    content = content.strip()
    if not content:
        return ""

    lines = content.split("\n")
    result_lines = []

    for line in lines:
        stripped_line = line.strip()

        # Check inline format: ===content===
        inline_match = COMPILED_INLINE_PRESERVE_REGEX.match(stripped_line)
        if inline_match:
            # Inline format, extract middle content
            inner_content = inline_match.group(1).strip()
            if inner_content and "===" not in inner_content:
                result_lines.append(inner_content)
        elif COMPILED_PRESERVE_FENCE_REGEX.match(stripped_line):  # type: ignore[unreachable]
            # Multiline format delimiter, skip
            continue
        else:
            # Normal content line, keep
            result_lines.append(line)

    return "\n".join(result_lines)


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

    # re module already imported at file top

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
