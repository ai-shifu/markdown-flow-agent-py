"""
Non-streaming Content Formatter

Processes complete content into a list of FormattedElements.
Mirrors Go formatter/format.go.
"""

from .classifier import Classifier
from .types import ClassifyResult, ElementType, FormattedElement, is_text_family


def format_content(content: str) -> list[FormattedElement]:
    """Format complete content into structured elements.

    Args:
        content: The full content string to format.

    Returns:
        A list of FormattedElement instances.
    """
    if not content:
        return []

    c = Classifier()
    elements: list[FormattedElement] = []
    current_number = 0
    last_html_number = 0
    last_type: str = ""
    started = False

    # Split by \n, consistent with streaming.
    # If content ends with \n, split produces a trailing empty string which we skip.
    lines = content.split("\n")
    if len(lines) > 0 and lines[-1] == "" and content.endswith("\n"):
        lines = lines[:-1]

    pending_newlines = 0

    for i, line in enumerate(lines):
        # Non-last lines get \n appended; last line only if original content didn't end with \n
        line_content = line + "\n" if i < len(lines) - 1 else line

        # Empty lines: buffer the \n instead of discarding
        if line.strip() == "":
            pending_newlines += 1
            continue

        # Consume pending newlines: append to previous element or prepend to current
        if pending_newlines > 0:
            extra = "\n" * pending_newlines
            if elements:
                elements[-1].content += extra
            else:
                line_content = extra + line_content
            pending_newlines = 0

        cr = c.classify_line(line)

        if cr.is_append:
            # script/style attaches to previous html block, revert to last html number
            current_number = last_html_number
        elif _should_new_number(started, cr, last_type):
            current_number += 1

        # Track last html block number
        if cr.type == ElementType.HTML and not cr.is_continuation and not cr.is_append:
            last_html_number = current_number

        elements.append(FormattedElement(content=line_content, type=cr.type, number=current_number))
        last_type = cr.type
        started = True

    # Trailing empty lines: append to last element
    if pending_newlines > 0 and elements:
        elements[-1].content += "\n" * pending_newlines

    return elements


def _should_new_number(started: bool, cr: ClassifyResult, last_type: str) -> bool:
    """Determine whether to increment the element number."""
    if not started:
        return False  # First element uses 0
    if cr.is_continuation:
        return False  # Inside existing block, don't increment
    # Note: is_append is handled separately before calling this function
    if is_text_family(cr.type) and is_text_family(last_type):
        return False  # title <-> text don't increment
    if cr.type == ElementType.HTML:
        return True  # Each new html block increments
    return cr.type != last_type  # Different type increments
