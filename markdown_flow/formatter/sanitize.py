"""
Content Sanitizer

Utilities for cleaning LLM-generated content before it is classified and
rendered.

Motivation
----------
LLMs intermittently wrap otherwise-renderable output (block-level HTML, SVG
infographics, plain narrative) in an *untagged* fenced code block, e.g. a bare
``` line with no info string, sometimes even leaving it unclosed. CommonMark
faithfully turns that region into a code block, so a renderer shows the raw
HTML source instead of the intended visual.

This module targets that specific artifact while preserving deliberate code
blocks. It relies on a simple, explicit convention: **source that is meant to
be displayed as code carries a language tag** (``` ```html ```, ``` ```python ```,
``` ```mermaid ```). An *untagged* fence therefore carries no "show the source"
intent and is treated as noise that can be removed so the wrapped content
renders normally.

The transformation is opt-in: callers apply it explicitly to generated content.
It does not change the behaviour of the classifier or ``format_content``.
"""

from ..parser.code_fence_utils import is_code_fence_end, parse_code_fence_start


def _fence_info_string(fence_line: str, fence_char: str) -> str:
    """Return the info string (language tag) of a fence opening line."""
    return fence_line.lstrip(" ").lstrip(fence_char).strip()


def strip_untagged_code_fences(content: str) -> str:
    """Remove untagged (language-less) code-fence markers from ``content``.

    An untagged fence is a fence opening line whose info string is empty
    (a bare ``` or ~~~ with no language). Such markers are dropped so the text
    they wrapped renders as normal Markdown/HTML instead of code. This handles
    both paired bare fences and a single unclosed/stray bare fence.

    Language-tagged fences (``` ```html ```, ``` ```mermaid ```, ...) and their
    contents are left untouched, including their bare closing fence line.

    Args:
        content: Raw content, typically LLM output.

    Returns:
        Content with untagged fence markers removed. Everything else, including
        the lines that were inside an untagged fence, is preserved verbatim.

    Examples:
        >>> strip_untagged_code_fences("```\\n<div>x</div>\\n```")
        '<div>x</div>'
        >>> strip_untagged_code_fences("```html\\n<div>x</div>\\n```")
        '```html\\n<div>x</div>\\n```'
    """
    if not content or ("```" not in content and "~~~" not in content):
        return content

    lines = content.split("\n")
    result: list[str] = []

    # When inside a language-tagged fence we copy lines verbatim until the
    # matching closing fence, so nested bare backticks and the closing fence
    # itself are preserved.
    inside_tagged_fence = False
    open_fence = None

    for line in lines:
        if inside_tagged_fence:
            result.append(line)
            if open_fence is not None and is_code_fence_end(line, open_fence):
                inside_tagged_fence = False
                open_fence = None
            continue

        fence = parse_code_fence_start(line)
        if fence is None:
            result.append(line)
            continue

        info = _fence_info_string(fence.line, fence.char)
        if info == "":
            # Untagged fence at the top level: drop the marker line, keep the
            # content it wrapped. Paired and unclosed bare fences both collapse
            # here because we never enter a fenced state for them.
            continue

        # Language-tagged fence: keep it and preserve everything up to its close.
        result.append(line)
        inside_tagged_fence = True
        open_fence = fence

    return "\n".join(result)
