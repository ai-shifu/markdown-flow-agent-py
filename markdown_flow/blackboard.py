"""
Blackboard Mode Processor for MarkdownFlow

Handles blackboard mode processing, which generates incremental HTML content
with synchronized narration for text-to-speech output.
"""

import json
from typing import Any, Generator, Optional

from .constants import (
    DEFAULT_BLACKBOARD_PROMPT,
    BLACKBOARD_HTML_HEADER,
)
from .llm import LLMProvider
from .models import BlackboardStep
from .parser.json_stream import JSONStreamParser, validate_and_parse_json


def process_blackboard_stream(
    llm_provider: LLMProvider,
    base_messages: list[dict[str, str]],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
) -> Generator[dict[str, Any], None, None]:
    """
    Process blackboard mode as a streaming generator.

    Yields dictionaries containing blackboard step information and metadata.

    Args:
        llm_provider: LLM provider instance
        base_messages: Base messages to send to LLM (already includes blackboard prompt in system message)
        model: Optional model override
        temperature: Optional temperature override

    Yields:
        Dict with structure:
        {
            "content": str,  # Raw JSON string
            "metadata": {
                "block_type": "blackboard",
                "type": str,  # "head" or "body"
                "action": str,  # Action type (create_container, append_to_container, etc.)
                "container_id": str | None,
                "zone_id": str | None,
                "html": str | None,
                "animation": str | None,
                "element_id": str | None,
                "params": dict,
                "narration": str,
                "blackboard_step": BlackboardStep
            }
        }

    Raises:
        ValueError: If JSON parsing fails or stream ends with incomplete data
        RuntimeError: If LLM stream encounters errors
    """
    # Output HTML header (CDN references and styles for <head>)
    # Note: header uses a special "head" action that skips validation
    header_step = BlackboardStep(
        action="head",  # Special action for header output
        narration="",
        html=BLACKBOARD_HTML_HEADER,
        type="head",
    )

    yield {
        "content": BLACKBOARD_HTML_HEADER,
        "metadata": {
            "block_type": "blackboard",
            "type": "head",
            "action": header_step.action,
            "html": header_step.html,
            "narration": header_step.narration,
            "blackboard_step": header_step,
        },
    }

    # Initialize JSON stream parser
    json_parser = JSONStreamParser()

    try:
        # Start LLM stream (base_messages already includes blackboard prompt)
        for chunk in llm_provider.stream(
            messages=base_messages,
            model=model,
            temperature=temperature,
        ):
            # Append chunk content to parser (chunk is already a string)
            if chunk:
                json_parser.append_data(chunk)

            # Extract all complete JSON objects from buffer
            while True:
                json_str, ok = json_parser.extract_next()
                if not ok:
                    break

                # Parse JSON into BlackboardStep
                try:
                    step = validate_and_parse_json(json_str, BlackboardStep)
                except (json.JSONDecodeError, ValueError) as e:
                    raise ValueError(f"Failed to parse blackboard step: {e}") from e

                # Yield result with metadata
                yield {
                    "content": json_str,
                    "metadata": {
                        "block_type": "blackboard",
                        "type": step.type,
                        # Action-based fields
                        "action": step.action,
                        "container_id": step.container_id,
                        "zone_id": step.zone_id,
                        "html": step.html,
                        "animation": step.animation,
                        "element_id": step.element_id,
                        "params": step.params,
                        "narration": step.narration,
                        # Include the full step object
                        "blackboard_step": step,
                    },
                }

                # Note: No longer checking is_complete flag
                # Stream will end naturally when LLM stops generating

        # Stream ended without is_complete=True
        # Check for remaining buffer (debugging info)
        remaining_buffer = json_parser.get_buffer()
        if remaining_buffer.strip():
            # Silently ignore - stream already ended normally
            pass

    except Exception as e:
        raise RuntimeError(f"LLM stream error during blackboard mode: {e}") from e


def get_blackboard_prompt(custom_prompt: Optional[str] = None) -> str:
    """
    Get the blackboard prompt to use.

    Args:
        custom_prompt: Custom blackboard prompt (optional)

    Returns:
        The blackboard prompt string (custom or default)
    """
    return custom_prompt or DEFAULT_BLACKBOARD_PROMPT


class BlackboardProcessor:
    """
    Convenience class for processing blackboard mode.

    Provides a cleaner interface for blackboard mode processing with
    configurable settings.

    Note:
        The blackboard_prompt parameter is deprecated. Blackboard prompt should now
        be included in the base_messages system message with <blackboard_mode> tags.
        Use MarkdownFlow.process_blackboard() for automatic prompt management.

    Example:
        >>> processor = BlackboardProcessor(llm_provider)
        >>> for result in processor.process(messages):
        ...     print(result["metadata"]["html"])
        ...     print(result["metadata"]["narration"])
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        blackboard_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize blackboard processor.

        Args:
            llm_provider: LLM provider instance
            blackboard_prompt: Custom blackboard prompt (optional)
            model: Default model to use (optional)
            temperature: Default temperature to use (optional)
        """
        self.llm_provider = llm_provider
        self.blackboard_prompt = blackboard_prompt
        self.model = model
        self.temperature = temperature

    def set_prompt(self, prompt: str) -> "BlackboardProcessor":
        """
        Set custom blackboard prompt.

        Args:
            prompt: Custom blackboard prompt

        Returns:
            Self for method chaining
        """
        self.blackboard_prompt = prompt
        return self

    def set_model(self, model: str) -> "BlackboardProcessor":
        """
        Set model to use.

        Args:
            model: Model name

        Returns:
            Self for method chaining
        """
        self.model = model
        return self

    def set_temperature(self, temperature: float) -> "BlackboardProcessor":
        """
        Set temperature to use.

        Args:
            temperature: Temperature value

        Returns:
            Self for method chaining
        """
        self.temperature = temperature
        return self

    def process(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Process blackboard mode with given messages.

        Args:
            messages: Base messages to send to LLM (list of dicts with 'role' and 'content')
            model: Optional model override (uses instance default if None)
            temperature: Optional temperature override (uses instance default if None)

        Yields:
            Blackboard step results with metadata

        Example:
            >>> for result in processor.process(messages):
            ...     step = result["metadata"]["blackboard_step"]
            ...     print(f"Step {step.step_number}: {step.html}")
        """
        return process_blackboard_stream(
            llm_provider=self.llm_provider,
            base_messages=messages,
            model=model or self.model,
            temperature=temperature or self.temperature,
        )
