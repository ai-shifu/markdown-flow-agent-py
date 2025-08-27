"""
Markdown-Flow Core Components

A powerful Python package for parsing and processing specially formatted Markdown documents.

Core Features:
    - Parse documents into blocks using --- and ?[] separators
    - Three-layer parsing architecture for complex interaction formats
    - Extract variable placeholders ({{variable}} and %{{variable}} formats)
    - Build LLM-ready prompts and message formats
    - Handle user interaction validation and input processing
    - Support multiple processing modes: PROMPT_ONLY, COMPLETE, STREAM

Supported Interaction Types:
    - TEXT_ONLY: ?[%{{var}}...question] - Text input only
    - BUTTONS_ONLY: ?[%{{var}} A|B] - Button selection only
    - BUTTONS_WITH_TEXT: ?[%{{var}} A|B|...question] - Buttons + text input
    - NON_ASSIGNMENT_BUTTON: ?[Continue|Cancel] - Display buttons only

Basic Usage:
    from markdown_flow import MarkdownFlow, ProcessMode

    # Create instance with LLM provider
    mf = MarkdownFlow(document, llm_provider=your_llm_provider)

    # Extract variables
    variables = mf.extract_variables()

    # Get all blocks
    blocks = mf.get_all_blocks()

    # Process blocks using unified interface
    result = await mf.process(0, variables={'name': 'John'}, mode=ProcessMode.COMPLETE)

    # Different processing modes
    prompt_result = await mf.process(0, mode=ProcessMode.PROMPT_ONLY)
    complete_result = await mf.process(0, mode=ProcessMode.COMPLETE)
    stream_result = await mf.process(0, mode=ProcessMode.STREAM)

Variable System:
    - {{variable}} - Regular variables, replaced with actual values
    - %{{variable}} - Preserved variables, kept in original format for LLM understanding

Import Guide:
    from markdown_flow import MarkdownFlow, ProcessMode, LLMProvider
    from markdown_flow import extract_variables_from_text, InteractionParser
    from markdown_flow import InteractionType, BlockType, InputType
"""

# Import core classes and enums
from .core import MarkdownFlow
from .enums import BlockType, InputType
from .llm import LLMProvider, LLMResult, ProcessMode
from .utils import (
    InteractionParser,
    InteractionType,
    extract_interaction_question,
    extract_variables_from_text,
    generate_smart_validation_template,
    replace_variables_in_text,
)


# Public API
__all__ = [
    # Core classes
    "MarkdownFlow",
    "InteractionParser",
    # LLM related
    "LLMProvider",
    "LLMResult",
    "ProcessMode",
    # Enumeration types
    "BlockType",
    "InputType",
    "InteractionType",
    # Main utility functions
    "generate_smart_validation_template",
    "extract_interaction_question",
    "extract_variables_from_text",
    "replace_variables_in_text",
]

__version__ = "0.2.3"
