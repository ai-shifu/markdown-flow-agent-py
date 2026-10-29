"""Projected containers retain browser-observed residual TAB label padding."""

import hashlib
import json
from pathlib import Path

import pytest

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans


OBSERVED_ROWS = json.loads(Path(__file__).with_name("reference-label-virtual-cases.json").read_text())["cases"]
OBSERVED_CASES = [(case, ending) for case in OBSERVED_ROWS for ending in case["line_endings"]]


@pytest.mark.parametrize(("case", "ending"), OBSERVED_CASES, ids=[case["id"] + "|" + ending for case, ending in OBSERVED_CASES])
def test_projected_tab_padding_matches_observed_images_and_named_answers(case, ending: str) -> None:
    captured = "".join(part if isinstance(part, str) else part[0] * part[1] for part in case["parts"])
    assert hashlib.sha256(captured.encode()).hexdigest() == case["sha256"]
    source = captured.replace("\n", {"LF": "\n", "CRLF": "\r\n", "CR": "\r"}[ending])
    control = "?[" + case["marker"] + " A | B]"
    questions = [control] if case["buttons"] else []
    assert bool(list(find_document_image_labels(source))) is case["image"]
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == questions
    replacement = source.replace("{{goal}}", "old") if case["image"] and case["marker"] == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement
    flow = MarkdownFlow(source)
    blocks = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in blocks] == questions
    if blocks:
        assert flow.process(blocks[0].index, variables={"goal": "old"}, user_input={"goal": ["B"]}).variables == {"goal": ["B"]}
