"""Image alternative text stays within its opening Markdown paragraph."""

import json
from pathlib import Path
from typing import Any

import pytest

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans


_CASES = json.loads(Path(__file__).with_name("image-alt-paragraph-observed-cases.json").read_text())["cases"]


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["id"])
def test_image_alt_paragraph_bounds_match_observed_controls_and_answers(case: dict[str, Any]) -> None:
    source = case["source"]
    visible = bool(case["observed"]["buttons"])
    assert len(list(find_document_image_labels(source))) == len(case["observed"]["images"])
    controls = [source[start:end] for start, end in find_document_interaction_spans(source)]
    expected = ["?[" + case["marker"] + " A | B]"] if visible else []
    assert controls == expected
    replacement = source if visible or case["marker"].startswith("%") else source.replace("{{goal}}", "old")
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == expected
    if questions:
        assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["B"]}).variables == {"goal": ["B"]}
