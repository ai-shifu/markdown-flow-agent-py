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
    CONTENT_HTML = "content_html"  # HTML generation blocks triggered by @html keyword

    def is_content_html(self) -> bool:
        """Check if this block type is CONTENT_HTML."""
        return self == BlockType.CONTENT_HTML
