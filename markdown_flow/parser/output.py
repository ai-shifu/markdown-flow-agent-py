"""
Output Parser Module

Handles output instructions and preserved content processing for MarkdownFlow documents.
"""

import re

from ..constants import (
    COMPILED_INLINE_PRESERVE_REGEX,
    COMPILED_PRESERVE_FENCE_REGEX,
    OUTPUT_INSTRUCTION_PREFIX,
    OUTPUT_INSTRUCTION_SUFFIX,
)


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
