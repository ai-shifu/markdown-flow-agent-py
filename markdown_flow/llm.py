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

    def __bool__(self):
        """Support boolean evaluation."""
        return bool(self.content or self.prompt or self.variables)


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    def complete(self, messages: list[dict[str, str]]) -> str:
        """
        Non-streaming LLM call.

        Args:
            messages: Message list in format [{"role": "system/user/assistant", "content": "..."}].
                      This list already includes conversation history context merged by MarkdownFlow.

        Returns:
            str: LLM response content

        Raises:
            ValueError: When LLM call fails
        """

    @abstractmethod
    def stream(self, messages: list[dict[str, str]]):
        """
        Streaming LLM call.

        Args:
            messages: Message list in format [{"role": "system/user/assistant", "content": "..."}].
                      This list already includes conversation history context merged by MarkdownFlow.

        Yields:
            str: Incremental LLM response content

        Raises:
            ValueError: When LLM call fails
        """


class NoLLMProvider(LLMProvider):
    """Empty LLM provider for prompt-only scenarios."""

    def complete(self, messages: list[dict[str, str]]) -> str:
        raise NotImplementedError(NO_LLM_PROVIDER_ERROR)

    def stream(self, messages: list[dict[str, str]]):
        raise NotImplementedError(NO_LLM_PROVIDER_ERROR)
