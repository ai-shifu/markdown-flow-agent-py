"""
Markdown-Flow Parser Module

Provides specialized parsers for different aspects of MarkdownFlow document processing.
"""

from .action_validator import validate_action, ALL_ACTIONS
from .interaction import InteractionParser, InteractionType, extract_interaction_question
from .json_parser import parse_json_response
from .output import (
    extract_preserved_content,
    is_preserved_content_block,
    process_output_instructions,
)
from .preprocessor import CodeBlockPreprocessor
from .validation import generate_smart_validation_template, parse_validation_response
from .variable import extract_variables_from_text, replace_variables_in_text


__all__ = [
    # Variable parsing
    "extract_variables_from_text",
    "replace_variables_in_text",
    # Interaction parsing
    "InteractionParser",
    "InteractionType",
    "extract_interaction_question",
    # Output and preserved content
    "is_preserved_content_block",
    "extract_preserved_content",
    "process_output_instructions",
    # Code block preprocessing
    "CodeBlockPreprocessor",
    # Validation
    "generate_smart_validation_template",
    "parse_validation_response",
    # JSON parsing
    "parse_json_response",
    # Action validation (blackboard mode)
    "validate_action",
    "ALL_ACTIONS",
]
