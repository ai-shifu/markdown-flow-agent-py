"""
JSON Stream Parser for MarkdownFlow Blackboard Mode

Provides utilities for extracting complete JSON objects from streaming data,
handling incomplete chunks and nested structures.
"""

import json
from typing import Optional


def extract_next_json(buffer: str) -> tuple[str, str, bool]:
    """
    Extract the next complete JSON object from a buffer.

    Uses a state machine to track brace depth and string context to identify
    complete JSON objects even when the buffer contains incomplete data.

    Args:
        buffer: String buffer potentially containing one or more JSON objects

    Returns:
        A tuple of (json_str, remaining, ok) where:
        - json_str: The extracted JSON string (empty if no complete object found)
        - remaining: The remaining buffer after extraction
        - ok: True if a complete JSON object was extracted, False otherwise

    Examples:
        >>> extract_next_json('{"a":1}{"b":2}')
        ('{"a":1}', '{"b":2}', True)

        >>> extract_next_json('{"a":1')
        ('', '{"a":1', False)

        >>> extract_next_json('{"msg":"Hello {world}"}')
        ('{"msg":"Hello {world}"}', '', True)
    """
    depth = 0
    start = -1
    in_string = False
    escape = False

    for i, ch in enumerate(buffer):
        # Handle escape sequences
        if escape:
            escape = False
            continue

        if ch == "\\":
            escape = True
            continue

        # Handle string boundaries
        if ch == '"':
            in_string = not in_string
            continue

        # Only process braces outside of strings
        if in_string:
            continue

        # Track brace depth
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                # Found a complete JSON object
                json_str = buffer[start : i + 1]
                remaining = buffer[i + 1 :]
                return json_str, remaining, True

    # No complete JSON object found
    return "", buffer, False


def extract_all_json(text: str) -> list[str]:
    """
    Extract all complete JSON objects from a text string.

    Args:
        text: String containing one or more JSON objects

    Returns:
        List of JSON strings

    Examples:
        >>> extract_all_json('{"a":1}{"b":2}{"c":3}')
        ['{"a":1}', '{"b":2}', '{"c":3}']
    """
    objects = []
    remaining = text

    while True:
        json_str, remaining, ok = extract_next_json(remaining)
        if not ok:
            break
        objects.append(json_str)

    return objects


class JSONStreamParser:
    """
    Incremental JSON stream parser for handling chunked data.

    Maintains an internal buffer and extracts complete JSON objects as they
    become available in the stream.

    Example:
        >>> parser = JSONStreamParser()
        >>> parser.append_data('{"a":1}')
        >>> parser.append_data('{"b":')
        >>> parser.append_data('2}{"c":3}')
        >>> parser.extract_next()
        ('{"a":1}', True)
        >>> parser.extract_next()
        ('{"b":2}', True)
        >>> parser.extract_next()
        ('{"c":3}', True)
        >>> parser.extract_next()
        ('', False)
    """

    def __init__(self):
        """Initialize the JSON stream parser with an empty buffer."""
        self._buffer: str = ""

    def append_data(self, data: str) -> None:
        """
        Append new data to the internal buffer.

        Args:
            data: New chunk of data to append
        """
        self._buffer += data

    def extract_next(self) -> tuple[str, bool]:
        """
        Extract the next complete JSON object from the buffer.

        Returns:
            A tuple of (json_str, ok) where:
            - json_str: The extracted JSON string
            - ok: True if extraction succeeded, False otherwise
        """
        json_str, remaining, ok = extract_next_json(self._buffer)
        if ok:
            self._buffer = remaining
        return json_str, ok

    def get_buffer(self) -> str:
        """
        Get the current buffer content.

        Returns:
            The current buffer string
        """
        return self._buffer

    def reset(self) -> None:
        """Reset the buffer to empty state."""
        self._buffer = ""


def validate_and_parse_json(json_str: str, target_class: Optional[type] = None) -> dict | object:
    """
    Validate and parse a JSON string, optionally converting to a target class.

    Args:
        json_str: JSON string to parse
        target_class: Optional dataclass or type to convert the parsed data into

    Returns:
        Parsed JSON as dict, or instance of target_class if provided

    Raises:
        json.JSONDecodeError: If the JSON string is invalid
        ValueError: If conversion to target_class fails

    Examples:
        >>> validate_and_parse_json('{"a":1,"b":2}')
        {'a': 1, 'b': 2}

        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class Example:
        ...     a: int
        ...     b: int
        >>> validate_and_parse_json('{"a":1,"b":2}', Example)
        Example(a=1, b=2)
    """
    # Parse JSON
    data = json.loads(json_str)

    # Convert to target class if specified
    if target_class is not None:
        try:
            if hasattr(target_class, "__annotations__"):
                # Dataclass conversion
                return target_class(**data)
            else:
                # Generic class conversion
                return target_class(data)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to convert to {target_class.__name__}: {e}") from e

    return data
