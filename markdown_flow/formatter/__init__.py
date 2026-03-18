"""
Formatter Package

Provides content classification and structured output for SSE streams.
"""

from .format import format_content
from .stream import StreamFormatter
from .types import ClassifyResult, ElementType, FormattedElement


__all__ = [
    "ElementType",
    "FormattedElement",
    "ClassifyResult",
    "format_content",
    "StreamFormatter",
]
