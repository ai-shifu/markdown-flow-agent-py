"""Consecutive image definitions retain the validated reference paragraph owner."""

import json
from pathlib import Path
from typing import Any

import pytest

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans


_CASES = json.loads(Path(__file__).with_name("indented-reference-definitions-observed-cases.json").read_text())["cases"]


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["id"])
def test_indented_reference_definitions_match_observed_images_and_real_answers(case: dict[str, Any]) -> None:
    source = case["source"]
    marker = case["marker"]
    visible = bool(set(case["buttons"]) & {"A", "B"})
    expected = ["?[" + marker + " A | B]"] if visible else []
    assert len(list(find_document_image_labels(source))) == case["images"]
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == expected
    replacement = source if visible or marker.startswith("%") else source.replace("{{goal}}", "old")
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == expected
    if questions:
        assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["B"]}).variables == {"goal": ["B"]}
    elif not marker.startswith("%"):
        prompt = flow.get_content_messages(0, {"goal": "old"})[-1]["content"]
        assert "old" in prompt
        assert "{{goal}}" not in prompt
