"""
Interaction Parser Module

Provides three-layer interaction parsing for MarkdownFlow ?[] format validation,
variable detection, and content parsing.
"""

from enum import Enum
from typing import Any

from ..constants import (
    COMPILED_INTERACTION_REGEX,
    COMPILED_LAYER1_INTERACTION_REGEX,
    COMPILED_LAYER2_VARIABLE_REGEX,
    COMPILED_LAYER3_ELLIPSIS_REGEX,
    COMPILED_SINGLE_PIPE_SPLIT_REGEX,
)


class InteractionType(Enum):
    """Interaction input type enumeration."""

    TEXT_ONLY = "text_only"  # Text input only: ?[%{{var}}...question]
    BUTTONS_ONLY = "buttons_only"  # Button selection only: ?[%{{var}} A|B]
    BUTTONS_WITH_TEXT = "buttons_with_text"  # Buttons + text: ?[%{{var}} A|B|...question]
    BUTTONS_MULTI_SELECT = "buttons_multi_select"  # Multi-select buttons: ?[%{{var}} A||B]
    BUTTONS_MULTI_WITH_TEXT = "buttons_multi_with_text"  # Multi-select + text: ?[%{{var}} A||B||...question]
    NON_ASSIGNMENT_BUTTON = "non_assignment_button"  # Display buttons: ?[Continue|Cancel]


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
