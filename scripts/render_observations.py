"""Captured learner-renderer corrections for older MarkdownIt-based fixtures."""

import hashlib
import json
from pathlib import Path


_CASES = {case["sha256"]: case for case in json.loads(Path(__file__).with_name("render-run-legacy-observed-cases.json").read_text())["cases"]}


def observed_rendering(source: str, fallback_image: bool) -> tuple[bool, bool]:
    """Return independent browser image/control observations when captured."""
    case = _CASES.get(hashlib.sha256(source.encode()).hexdigest())
    if case is None:
        return fallback_image, not fallback_image
    assert case["source"] == source
    return bool(case["images"]), bool(set(case["buttons"]) & {"A", "B"})
