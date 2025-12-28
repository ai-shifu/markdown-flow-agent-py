"""
Markdown-Flow LLM Integration Module

Provides LLM provider interfaces and related data models, supporting multiple processing modes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .constants import NO_LLM_PROVIDER_ERROR


class ProcessMode(Enum):
    """LLM processing modes."""

    COMPLETE = "complete"  # Complete processing (non-streaming)
    STREAM = "stream"  # Streaming processing


@dataclass
class LLMResult:
    """Unified LLM processing result."""

    content: str = ""  # Final content
    prompt: str | None = None  # Used prompt
    variables: dict[str, str | list[str]] | None = None  # Extracted variables
    metadata: dict[str, Any] | None = None  # Metadata
    transformed_to_interaction: bool = False  # Whether transformed to interaction (for Function Calling)

    def __bool__(self):
        """Support boolean evaluation."""
        return bool(self.content or self.prompt or self.variables)


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    def complete(self, messages: list[dict[str, str]], model: str | None = None, temperature: float | None = None) -> LLMResult:
        """
        Non-streaming LLM call.

        Args:
            messages: Message list in format [{"role": "system/user/assistant", "content": "..."}].
                      This list already includes conversation history context merged by MarkdownFlow.
            model: Optional model name override
            temperature: Optional temperature override

        Returns:
            LLMResult: Complete result with content, metadata, and optional fields like transformed_to_interaction

        Raises:
            ValueError: When LLM call fails
        """

    @abstractmethod
    def stream(self, messages: list[dict[str, str]], model: str | None = None, temperature: float | None = None):
        """
        Streaming LLM call.

        Args:
            messages: Message list in format [{"role": "system/user/assistant", "content": "..."}].
                      This list already includes conversation history context merged by MarkdownFlow.
            model: Optional model name override
            temperature: Optional temperature override

        Yields:
            str: Incremental LLM response content

        Raises:
            ValueError: When LLM call fails
        """


class NoLLMProvider(LLMProvider):
    """Empty LLM provider for prompt-only scenarios."""

    def complete(self, messages: list[dict[str, str]], model: str | None = None, temperature: float | None = None, max_tokens: int | None = None) -> LLMResult:
        raise NotImplementedError(NO_LLM_PROVIDER_ERROR)

    def stream(self, messages: list[dict[str, str]], model: str | None = None, temperature: float | None = None, max_tokens: int | None = None):
        raise NotImplementedError(NO_LLM_PROVIDER_ERROR)
