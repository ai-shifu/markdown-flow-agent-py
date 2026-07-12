"""
Default MDF system prompt for MarkdownFlow.

Contains content processing rules (always active) and visual mode rules
(self-gated, only active when user explicitly requests visual content).

This prompt defines framework constraints only. Device-specific adaptations
(container size, min font size, etc.) should be injected via set_viewing_mode_prompt.
"""

from pathlib import Path


DEFAULT_MDF_SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text(encoding="utf-8")
HIGHER_PRIORITY_INSTRUCTIONS_PROMPT = (Path(__file__).parent / "higher_priority_prompt.md").read_text(encoding="utf-8").strip()
