"""
Markdown-Flow Data Model Definitions

Simplified and refactored data models focused on core functionality.
"""

from dataclasses import dataclass, field
from typing import Any

from .enums import BlockType, InputType
from .parser import extract_variables_from_text


@dataclass
class UserInput:
    """
    Simplified user input data class.

    Attributes:
        content (dict[str, list[str]]): User input content as variable name to values mapping
        input_type (InputType): Input method, defaults to text input
        is_multi_select (bool): Whether this contains multi-select input, defaults to False
    """

    content: dict[str, list[str]]
    input_type: InputType = InputType.TEXT
    is_multi_select: bool = False


@dataclass
class Block:
    """
    Simplified document block data class.

    Attributes:
        content (str): Block content
        block_type (Union[BlockType, str]): Block type
        index (int): Block index, defaults to 0
        variables (List[str]): List of variable names contained in the block
    """

    content: str
    block_type: BlockType | str
    index: int = 0
    variables: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Post-initialization processing."""
        # Convert to BlockType enum
        if isinstance(self.block_type, str):
            # Efficient type mapping
            type_mapping = {
                "content": BlockType.CONTENT,
                "interaction": BlockType.INTERACTION,
                "preserved_content": BlockType.PRESERVED_CONTENT,
            }

            self.block_type = type_mapping.get(self.block_type, self._parse_block_type_fallback(self.block_type))

        # Auto-extract variables
        if not self.variables:
            self.variables = extract_variables_from_text(self.content)

    def _parse_block_type_fallback(self, block_type_str: str) -> BlockType:
        """Fallback logic for non-standard block_type strings."""
        try:
            return BlockType(block_type_str)
        except ValueError:
            return BlockType.CONTENT

    @property
    def is_interaction(self) -> bool:
        """Check if this is an interaction block."""
        return self.block_type == BlockType.INTERACTION

    @property
    def is_content(self) -> bool:
        """Check if this is a content block."""
        return self.block_type in [BlockType.CONTENT, BlockType.PRESERVED_CONTENT]


@dataclass
class BlackboardStep:
    """
    Blackboard mode step with action-based container management.

    Each step represents a single action on the blackboard (create container,
    append content, highlight element, etc.) rather than direct HTML output.

    Narration Strategy (两层策略):
    - Container-level actions (create_container, set_canvas_layout, activate_zone):
      Provide COMPLETE narration for entire section (50-200 chars)
    - Element-level actions (append_to_container, update_element):
      Optional narration (usually empty, 不需要narration)
    - This allows TTS to play full sentences while HTML renders incrementally

    Attributes:
        action (str): Action type - "append_to_container", "annotate", etc. (required)
        narration (str): Narration for TTS (empty for element-level actions, default: "")
        container_id (str | None): Container unique identifier (optional)
        zone_id (str | None): Zone identifier where container resides (optional)
        html (str | None): HTML content to append/replace (optional)
        animation (str | None): Animation effect - "slide_in", "fade_in", "write", etc. (optional)
        element_id (str | None): Element identifier for updates/annotations (optional)
        params (dict[str, Any]): Flexible parameter storage for action-specific data (default: {})
        type (str): Step type - "head" or "body" (default: "body", legacy field)
        metadata (dict[str, Any]): Additional metadata (default: {}, legacy field)
    """

    # Required field
    action: str

    # Optional fields (action-specific)
    narration: str = ""
    container_id: str | None = None
    zone_id: str | None = None
    html: str | None = None
    animation: str | None = None
    element_id: str | None = None

    # Flexible parameter storage
    params: dict[str, Any] = field(default_factory=dict)

    # Legacy fields (for compatibility)
    type: str = "body"  # "head" or "body"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate action fields."""
        if not self.action:
            raise ValueError("action field is required")

        # Narration required only for container-level actions
        CONTAINER_LEVEL_ACTIONS = [
            "create_container",
            "set_canvas_layout",
            "activate_zone",
        ]

        if self.action in CONTAINER_LEVEL_ACTIONS and not self.narration and self.type != "head":
            raise ValueError(
                f"{self.action} requires narration (provide complete narration for entire section)"
            )

        # Import validator to avoid circular dependency
        # Will validate after action_validator module is created
        try:
            from .parser.action_validator import validate_action

            is_valid, error = validate_action(self)
            if not is_valid:
                raise ValueError(f"Invalid action: {error}")
        except ImportError:
            # action_validator module not yet created, skip validation
            pass
