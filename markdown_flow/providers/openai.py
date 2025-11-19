"""
OpenAI-Compatible Provider Implementation

Provides a production-ready OpenAI-compatible LLM provider with debug mode,
token tracking, and comprehensive metadata.
"""

import time
from collections.abc import Generator
from typing import Any

from ..llm import LLMProvider
from .config import ProviderConfig


try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[misc, assignment]


class OpenAIProvider(LLMProvider):
    """
    OpenAI-compatible LLM provider implementation.

    Features:
    - Debug mode with colorized console output
    - Automatic token usage tracking
    - Comprehensive metadata (model, temperature, processing time, tokens, timestamp)
    - Instance-level model/temperature override support
    - Streaming and non-streaming modes
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize OpenAI provider.

        Args:
            config: Provider configuration

        Raises:
            ImportError: If openai package is not installed
            ValueError: If configuration is invalid
        """
        if OpenAI is None:
            raise ImportError("The 'openai' package is required for OpenAIProvider. Install it with: pip install openai")

        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
        )
        self._last_metadata: dict[str, Any] = {}

    def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """
        Non-streaming LLM call.

        Args:
            messages: Message list
            model: Optional model override
            temperature: Optional temperature override

        Returns:
            LLM response content

        Raises:
            Exception: If API call fails
        """
        # Determine actual model and temperature (instance override > provider default)
        actual_model = model if model is not None else self.config.model
        actual_temperature = temperature if temperature is not None else self.config.temperature

        # Debug output: Request info
        if self.config.debug:
            self._print_request_info(messages, actual_model, actual_temperature)

        # Format messages
        formatted_messages = self._format_messages(messages)

        # Record start time
        start_time = time.time()

        try:
            # Make API call
            response = self.client.chat.completions.create(
                model=actual_model,
                messages=formatted_messages,
                temperature=actual_temperature,
            )

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Extract content
            if not response.choices or len(response.choices) == 0:
                raise Exception("API response error: no choices returned")

            choice = response.choices[0]
            if not choice.message:
                raise Exception("Response has no message field")

            content = choice.message.content or ""

            # Extract token usage
            usage = response.usage
            metadata = {
                "model": actual_model,
                "temperature": actual_temperature,
                "provider": "openai-compatible",
                "processing_time": processing_time_ms,
                "timestamp": int(time.time()),
            }

            if usage:
                metadata.update(
                    {
                        "prompt_tokens": usage.prompt_tokens,
                        "output_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens,
                    }
                )

            # Save metadata for retrieval by MarkdownFlow
            self._last_metadata = metadata

            # Debug output: Response metadata
            if self.config.debug:
                self._print_response_metadata(metadata)

            return content

        except Exception as e:
            raise Exception(f"API request failed: {str(e)}") from e

    def stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
    ) -> Generator[str, None, None]:
        """
        Streaming LLM call.

        Args:
            messages: Message list
            model: Optional model override
            temperature: Optional temperature override

        Yields:
            Incremental LLM response content

        Raises:
            Exception: If API call fails
        """
        # Determine actual model and temperature
        actual_model = model if model is not None else self.config.model
        actual_temperature = temperature if temperature is not None else self.config.temperature

        # Debug output: Request info
        if self.config.debug:
            self._print_request_info(messages, actual_model, actual_temperature)

        # Format messages
        formatted_messages = self._format_messages(messages)

        # Record start time
        start_time = time.time()

        try:
            # Create streaming response
            stream = self.client.chat.completions.create(
                model=actual_model,
                messages=formatted_messages,
                temperature=actual_temperature,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            # Calculate processing time after stream completes
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Save metadata for retrieval by MarkdownFlow
            metadata = {
                "model": actual_model,
                "temperature": actual_temperature,
                "provider": "openai-compatible",
                "processing_time": processing_time_ms,
                "timestamp": int(time.time()),
                "stream_done": True,
            }
            self._last_metadata = metadata

            # Debug output: Stream completion info
            if self.config.debug:
                self._print_response_metadata(metadata)

        except Exception as e:
            raise ValueError(f"Streaming request failed: {str(e)}") from e

    def get_last_metadata(self) -> dict[str, Any]:
        """
        Get metadata from the last LLM call.

        This method allows MarkdownFlow to retrieve comprehensive metadata including
        token usage, processing time, and other information from the most recent
        complete() or stream() call.

        Returns:
            Dictionary containing metadata:
            - model: Model name used
            - temperature: Temperature value used
            - provider: Provider identifier
            - processing_time: Processing time in milliseconds
            - timestamp: Unix timestamp
            - prompt_tokens: Number of input tokens (if available)
            - output_tokens: Number of output tokens (if available)
            - total_tokens: Total tokens (if available)
            - stream_done: True if this was a completed stream (stream mode only)

        Example:
            >>> provider = create_default_provider()
            >>> content = provider.complete(messages)
            >>> metadata = provider.get_last_metadata()
            >>> print(f"Used {metadata['total_tokens']} tokens")
        """
        return self._last_metadata.copy()

    def _format_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """
        Format messages for API call.

        Args:
            messages: Raw message list

        Returns:
            Formatted message list
        """
        formatted = []
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                formatted.append(
                    {
                        "role": msg["role"],
                        "content": str(msg["content"]),
                    }
                )
            else:
                # Fallback for non-standard format
                formatted.append(
                    {
                        "role": "user",
                        "content": str(msg),
                    }
                )
        return formatted

    def _print_request_info(self, messages: list[dict[str, str]], model: str, temperature: float) -> None:
        """
        Print colorized request information to console (debug mode).

        Args:
            messages: Message list
            model: Model name
            temperature: Temperature value
        """
        print("\033[97m\033[44m[ ====== LLM Request Start ====== ]\033[0m")
        print(f"\033[30m\033[42mmodel\033[0m: {model}")
        print(f"\033[30m\033[42mtemperature\033[0m: {temperature}")

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            # Truncate long content for readability
            display_content = content
            print(f"\033[30m\033[43m{role}\033[0m: {display_content}")

        print("\033[97m\033[44m[ ====== LLM Request End ====== ]\033[0m")

    def _print_response_metadata(self, metadata: dict[str, Any]) -> None:
        """
        Print colorized response metadata to console (debug mode).

        Args:
            metadata: Response metadata dictionary
        """
        print("\n\033[97m\033[42m[ ====== LLM Response Metadata ====== ]\033[0m")

        # Essential fields
        print(f"\033[36mmodel:\033[0m {metadata.get('model', 'N/A')}")
        print(f"\033[36mtemperature:\033[0m {metadata.get('temperature', 'N/A')}")
        print(f"\033[36mprovider:\033[0m {metadata.get('provider', 'N/A')}")
        print(f"\033[36mprocessing_time:\033[0m {metadata.get('processing_time', 'N/A')} ms")

        # Token usage (if available)
        if "prompt_tokens" in metadata:
            print(
                f"\033[36mprompt_tokens:\033[0m \033[33m{metadata['prompt_tokens']}\033[0m  "
                f"\033[36moutput_tokens:\033[0m \033[33m{metadata['output_tokens']}\033[0m  "
                f"\033[36mtotal_tokens:\033[0m \033[32m{metadata['total_tokens']}\033[0m"
            )

        print(f"\033[36mtimestamp:\033[0m {metadata.get('timestamp', 'N/A')}")

        if metadata.get("stream_done"):
            print("\033[36mstream:\033[0m completed")

        print("\033[97m\033[42m[ ====== ======================= ====== ]\033[0m")


def create_provider(config: ProviderConfig | None = None) -> OpenAIProvider:
    """
    Create an OpenAI provider instance.

    Args:
        config: Optional provider configuration. If None, uses default config
                (reads from environment variables).

    Returns:
        OpenAIProvider instance

    Raises:
        ValueError: If configuration is invalid
        ImportError: If openai package is not installed

    Example:
        >>> config = ProviderConfig(api_key="sk-...", model="gpt-4")
        >>> provider = create_provider(config)
    """
    if config is None:
        config = ProviderConfig()
    return OpenAIProvider(config)


def create_default_provider() -> OpenAIProvider:
    """
    Create an OpenAI provider with default configuration.

    Reads configuration from environment variables:
    - LLM_API_KEY: API key (required)
    - LLM_BASE_URL: Base URL (default: https://api.openai.com/v1)
    - LLM_MODEL: Model name (default: gpt-3.5-turbo)
    - LLM_TEMPERATURE: Temperature (default: 0.7)
    - LLM_DEBUG: Debug mode (default: false)
    - LLM_TIMEOUT: Request timeout in seconds (default: None, no timeout)

    Returns:
        OpenAIProvider instance with default config

    Raises:
        ValueError: If LLM_API_KEY is not set
        ImportError: If openai package is not installed

    Example:
        >>> # Set environment variable first
        >>> import os
        >>> os.environ["LLM_API_KEY"] = "sk-..."
        >>> provider = create_default_provider()
    """
    return create_provider()
