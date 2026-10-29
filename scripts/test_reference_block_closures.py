"""Definition lookahead follows observed ContentRender paragraph boundaries."""

import json
from pathlib import Path
from typing import Any

import pytest

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.constants import COMPILED_INLINE_HTML_REGEX
from markdown_flow.enums import BlockType
from markdown_flow.parser import document_blocks
from markdown_flow.parser.document_blocks import DocumentBlocks
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans


_CASES = json.loads(Path(__file__).with_name("reference-definition-paragraph-observed-cases.json").read_text())["cases"]


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["id"])
def test_reference_definition_lookahead_matches_observed_content_render(case: dict[str, Any]) -> None:
    """A definition retains the paragraph lookahead seen by the actual learner UI."""
    source = case["source"]
    image = bool(case["images"])
    spelling = case["marker"]
    control = "?[" + spelling + " A | B]"
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ([] if image else [control])
    replacement = source.replace("{{goal}}", "old") if image and spelling == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement
    flow = MarkdownFlow(source)
    # Existing comment preprocessing intentionally changes the source grammar.
    assert flow._processed_document == case.get("processedSource", source)
    flow_image = bool(case.get("processedImages", case["images"]))
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ([] if flow_image else [control])
    if questions:
        assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["A"]}).variables == {"goal": ["A"]}


@pytest.mark.parametrize("size", [100, 200, 400])
@pytest.mark.parametrize("unit", ["[one]: /one\n", "> [o\n> ne]: /one\n", '> [one]: /one "a\n> line\n> b"\n'])
def test_reference_closure_lookahead_has_bounded_work(monkeypatch: pytest.MonkeyPatch, size: int, unit: str) -> None:
    calls = 0
    original = document_blocks.DocumentBlocks.reference_projection

    def counted(self: DocumentBlocks, index: int, steps: tuple[int, ...]) -> tuple[int, str, bool, int]:
        nonlocal calls
        calls += 1
        return original(self, index, steps)

    monkeypatch.setattr(DocumentBlocks, "reference_projection", counted)
    blocks = DocumentBlocks(unit * size, COMPILED_INLINE_HTML_REGEX)
    assert calls <= 8 * len(blocks.lines)
