"""
Markdown-Flow Enumeration Definitions

Defines various enumeration types used throughout the system, including input types and block types.
"""

from enum import Enum


class InputType(Enum):
    """
    User input type enumeration.

    Defines the available input methods for user interactions.
    """

    CLICK = "click"  # Click-based selection from predefined options
    TEXT = "text"  # Free-form text input


class BlockType(Enum):
    """
    Document block type enumeration.

    Defines different types of blocks identified during document parsing.
    """

    CONTENT = "content"  # Regular document content blocks
    INTERACTION = "interaction"  # Interactive blocks requiring user input
    PRESERVED_CONTENT = "preserved_content"  # Special blocks: inline !===content!=== or multiline !===...!===


class ProcessingMode(Enum):
    """
    Processing mode enumeration.

    Defines the processing paradigm for MarkdownFlow document processing.
    """

    STANDARD = "standard"  # Standard mode: normal content processing
    BLACKBOARD = "blackboard"  # Blackboard mode: incremental HTML + narration output
