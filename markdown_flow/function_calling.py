"""
Markdown-Flow Function Calling Module

This module provides Function Calling tools and utilities for dynamic interaction generation.
It handles the conversion of natural language content into structured interaction blocks.
"""

# Define Function Calling tools for dynamic interaction detection
DYNAMIC_INTERACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_interaction_block",
            "description": "Convert content to interaction block with structured data when it needs to collect user input",
            "parameters": {
                "type": "object",
                "properties": {
                    "needs_interaction": {
                        "type": "boolean",
                        "description": "Whether this content needs to be converted to interaction block",
                    },
                    "variable_name": {
                        "type": "string",
                        "description": "Name of the variable to collect (without {{}} brackets)",
                    },
                    "interaction_type": {
                        "type": "string",
                        "enum": ["single_select", "multi_select", "text_input", "mixed"],
                        "description": "Type of interaction: single_select (|), multi_select (||), text_input (...), mixed (options + text)",
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of selectable options (3-4 specific options based on context)",
                    },
                    "allow_text_input": {
                        "type": "boolean",
                        "description": "Whether to include a text input option for 'Other' cases",
                    },
                    "text_input_prompt": {
                        "type": "string",
                        "description": "Prompt text for the text input option (e.g., '其他请输入', 'Other, please specify')",
                    },
                },
                "required": ["needs_interaction"],
            },
        },
    }
]


def build_interaction_format(tool_args: dict) -> str:
    """
    Build MarkdownFlow interaction format from structured Function Calling data.

    This function takes structured data returned from the LLM's Function Calling
    and constructs the proper MarkdownFlow interaction format string.

    Args:
        tool_args: Dictionary containing interaction parameters:
            - variable_name: Name of the variable to collect
            - interaction_type: Type of interaction (single_select, multi_select, text_input, mixed)
            - options: List of selectable options
            - allow_text_input: Whether to include text input option
            - text_input_prompt: Prompt text for the text input option

    Returns:
        MarkdownFlow interaction format string (e.g., "?[%{{variable}} option1|option2]")
        or empty string if required parameters are missing

    Example:
        >>> tool_args = {
        ...     "variable_name": "preference",
        ...     "interaction_type": "multi_select",
        ...     "options": ["Python", "JavaScript", "Go"],
        ...     "allow_text_input": True,
        ...     "text_input_prompt": "其他语言"
        ... }
        >>> build_interaction_format(tool_args)
        '?[%{{preference}} Python||JavaScript||Go||...其他语言]'
    """
    variable_name = tool_args.get("variable_name", "")
    interaction_type = tool_args.get("interaction_type", "single_select")
    options = tool_args.get("options", [])
    allow_text_input = tool_args.get("allow_text_input", False)
    text_input_prompt = tool_args.get("text_input_prompt", "...请输入")

    if not variable_name:
        return ""

    # For text_input type, options can be empty
    if interaction_type != "text_input" and not options:
        return ""

    # Choose separator based on interaction type
    if interaction_type in ["multi_select", "mixed"]:
        separator = "||"
    else:
        separator = "|"

    # Build options string
    if interaction_type == "text_input":
        # Text input only
        options_str = f"...{text_input_prompt}"
    else:
        # Options with potential text input
        options_str = separator.join(options)

        if allow_text_input and text_input_prompt:
            # Ensure text input has ... prefix
            text_option = text_input_prompt if text_input_prompt.startswith("...") else f"...{text_input_prompt}"
            options_str += f"{separator}{text_option}"

    return f"?[%{{{{{variable_name}}}}} {options_str}]"
