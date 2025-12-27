"""
Provider Configuration Module

Provides configuration classes for LLM providers.
"""

import os
from dataclasses import dataclass, field


def _parse_float_env(env_var: str, default: str, var_name: str) -> float:
    """
    Safely parse float from environment variable.

    Args:
        env_var: Environment variable name
        default: Default value as string
        var_name: Variable name for error messages

    Returns:
        Parsed float value

    Raises:
        ValueError: If environment variable contains invalid float value
    """
    value_str = os.getenv(env_var, default)
    try:
        return float(value_str)
    except ValueError as e:
        raise ValueError(
            f"Invalid {var_name} value in {env_var} environment variable: '{value_str}'. "
            f"Expected a numeric value (e.g., '0.7')."
        ) from e


def _parse_optional_float_env(env_var: str) -> float | None:
    """
    Safely parse optional float from environment variable.

    Args:
        env_var: Environment variable name

    Returns:
        Parsed float value or None if not set

    Raises:
        ValueError: If environment variable contains invalid float value
    """
    value_str = os.getenv(env_var)
    if not value_str:
        return None
    try:
        return float(value_str)
    except ValueError as e:
        raise ValueError(
            f"Invalid timeout value in {env_var} environment variable: '{value_str}'. "
            f"Expected a numeric value (e.g., '300.0')."
        ) from e


@dataclass
class ProviderConfig:
    """
    Configuration for LLM providers.

    Supports environment variable defaults for easy configuration.
    """

    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    """API key for the LLM service. Default: LLM_API_KEY environment variable."""

    base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"))
    """Base URL for the API endpoint. Default: LLM_BASE_URL environment variable or OpenAI default."""

    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-3.5-turbo"))
    """Default model name. Default: LLM_MODEL environment variable or gpt-3.5-turbo."""

    temperature: float = field(default_factory=lambda: _parse_float_env("LLM_TEMPERATURE", "0.7", "temperature"))
    """Default temperature (0.0-2.0). Default: LLM_TEMPERATURE environment variable or 0.7."""

    debug: bool = field(default_factory=lambda: os.getenv("LLM_DEBUG", "false").lower() in ("true", "1", "yes"))
    """Enable debug mode (colorized console output). Default: LLM_DEBUG environment variable or False."""

    timeout: float | None = field(default_factory=lambda: _parse_optional_float_env("LLM_TIMEOUT"))
    """Request timeout in seconds. None means no timeout. Default: LLM_TIMEOUT environment variable or None."""

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.api_key:
            raise ValueError("API key is required. Set it via ProviderConfig(api_key='...') or LLM_API_KEY environment variable.")

        if self.temperature < 0.0 or self.temperature > 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {self.temperature}")

        if self.timeout is not None and self.timeout <= 0:
            raise ValueError(f"Timeout must be positive or None, got {self.timeout}")
