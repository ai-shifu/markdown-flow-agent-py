"""
Action validator for blackboard container management.

Validates action-based blackboard steps to ensure proper structure
and required fields before frontend processing.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import BlackboardStep

# Action type constants
CANVAS_ACTIONS = [
    "set_canvas_layout",  # Initialize canvas layout
    "clear_canvas",  # Clear entire blackboard
]

ZONE_ACTIONS = [
    "activate_zone",  # Focus on specific zone
    "clear_zone",  # Clear zone content
]

CONTAINER_ACTIONS = [
    "create_container",  # Create new container
    "append_to_container",  # Append content (MOST COMMON)
    "replace_container",  # Replace container content
    "update_element",  # Update specific element
    "remove_container",  # Delete container
    "move_container",  # Move container to another zone
]

SPECIAL_ACTIONS = [
    "parallel",  # Execute multiple actions in parallel
    "sequence",  # Execute actions in sequence
    "annotate",  # Highlight/annotate element
]

ALL_ACTIONS = CANVAS_ACTIONS + ZONE_ACTIONS + CONTAINER_ACTIONS + SPECIAL_ACTIONS


def validate_action(step: "BlackboardStep") -> tuple[bool, str]:
    """
    Validate a blackboard action step.

    Args:
        step: BlackboardStep instance to validate

    Returns:
        (is_valid, error_message) tuple
        - is_valid: True if step is valid
        - error_message: Empty if valid, error description otherwise
    """
    # Skip validation for header type
    if step.type == "head":
        return True, ""

    # Check action field exists
    if not step.action:
        return False, "Missing required field: action"

    # Check action type is valid
    if step.action not in ALL_ACTIONS:
        return False, f"Unknown action type: {step.action}. Valid types: {', '.join(ALL_ACTIONS)}"

    # Action-specific validation
    validators = {
        "create_container": _validate_create_container,
        "append_to_container": _validate_append,
        "replace_container": _validate_replace,
        "update_element": _validate_update_element,
        "remove_container": _validate_remove,
        "move_container": _validate_move,
        "annotate": _validate_annotate,
        "set_canvas_layout": _validate_set_canvas_layout,
        "activate_zone": _validate_activate_zone,
        "clear_zone": _validate_clear_zone,
        "clear_canvas": _validate_clear_canvas,
        "parallel": _validate_parallel,
        "sequence": _validate_sequence,
    }

    validator = validators.get(step.action)
    if validator:
        return validator(step)

    # No specific validator, accept as valid
    return True, ""


# ========== Validator Functions ==========


def _validate_create_container(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate create_container action."""
    if not step.container_id:
        return False, "create_container requires container_id"
    if not step.zone_id:
        return False, "create_container requires zone_id"
    return True, ""


def _validate_append(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate append_to_container action."""
    if not step.container_id:
        return False, "append_to_container requires container_id"
    if not step.html:
        return False, "append_to_container requires html"

    # Narration NOT required for element-level actions
    # (Complete narration provided at container level)

    # Recommend keeping HTML small
    if step.html and len(step.html) > 500:
        # Warning, but not error
        pass

    return True, ""


def _validate_replace(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate replace_container action."""
    if not step.container_id:
        return False, "replace_container requires container_id"
    if not step.html:
        return False, "replace_container requires html"
    return True, ""


def _validate_update_element(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate update_element action."""
    if not step.container_id:
        return False, "update_element requires container_id"
    if not step.element_id:
        return False, "update_element requires element_id"
    if not step.html:
        return False, "update_element requires html"
    return True, ""


def _validate_remove(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate remove_container action."""
    if not step.container_id:
        return False, "remove_container requires container_id"
    return True, ""


def _validate_move(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate move_container action."""
    if not step.container_id:
        return False, "move_container requires container_id"
    # to_zone should be in params
    if not step.params.get("to_zone"):
        return False, "move_container requires params.to_zone"
    return True, ""


def _validate_annotate(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate annotate action."""
    if not step.container_id:
        return False, "annotate requires container_id"
    if not step.element_id:
        return False, "annotate requires element_id"

    # Check annotation params
    annotation = step.params.get("annotation", {})
    if not annotation:
        return False, "annotate requires params.annotation"

    if "type" not in annotation:
        return False, "annotation must have 'type' field (circle/underline/arrow/box)"

    return True, ""


def _validate_set_canvas_layout(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate set_canvas_layout action."""
    layout = step.params.get("layout")
    if not layout:
        return False, "set_canvas_layout requires params.layout"

    valid_layouts = ["single", "split_vertical", "split_horizontal", "grid"]
    if layout not in valid_layouts:
        return False, f"Invalid layout: {layout}. Must be one of: {', '.join(valid_layouts)}"

    if "zones" not in step.params:
        return False, "set_canvas_layout requires params.zones (array of zone IDs)"

    return True, ""


def _validate_activate_zone(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate activate_zone action."""
    if not step.zone_id:
        return False, "activate_zone requires zone_id"
    return True, ""


def _validate_clear_zone(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate clear_zone action."""
    if not step.zone_id:
        return False, "clear_zone requires zone_id"
    return True, ""


def _validate_clear_canvas(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate clear_canvas action."""
    # No specific requirements
    return True, ""


def _validate_parallel(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate parallel action."""
    actions = step.params.get("actions", [])
    if not actions:
        return False, "parallel requires params.actions (array of actions)"
    if not isinstance(actions, list):
        return False, "params.actions must be an array"
    return True, ""


def _validate_sequence(step: "BlackboardStep") -> tuple[bool, str]:
    """Validate sequence action."""
    actions = step.params.get("actions", [])
    if not actions:
        return False, "sequence requires params.actions (array of actions)"
    if not isinstance(actions, list):
        return False, "params.actions must be an array"
    return True, ""
