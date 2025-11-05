"""
JSON Parser Module

Provides robust JSON parsing with support for code blocks and mixed text formats.
"""

import json
import re
from typing import Any

from ..constants import JSON_PARSE_ERROR


def parse_json_response(response_text: str) -> dict[str, Any]:
    """
    Parse JSON response supporting multiple formats.

    Supports pure JSON strings, ```json code blocks, and mixed text formats.

    Args:
        response_text: Response text to parse

    Returns:
        Parsed dictionary object

    Raises:
        ValueError: When JSON cannot be parsed
    """
    text = response_text.strip()

    # Extract JSON code block
    if "```json" in text:
        start_idx = text.find("```json") + 7
        end_idx = text.find("```", start_idx)
        if end_idx != -1:
            text = text[start_idx:end_idx].strip()
    elif "```" in text:
        start_idx = text.find("```") + 3
        end_idx = text.find("```", start_idx)
        if end_idx != -1:
            text = text[start_idx:end_idx].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract first JSON object
        json_match = re.search(r"\{[^}]+\}", text)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError(JSON_PARSE_ERROR)
