"""Reference budgets match recorded browser observations, including physical columns."""

import json
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.constants import COMPILED_INLINE_HTML_REGEX
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_blocks import DocumentBlocks
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans


BROWSER_CASES = json.loads(Path(__file__).with_name("reference-label-budget-cases.json").read_text())["cases"]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("case", BROWSER_CASES, ids=lambda case: case["id"])
def test_reference_label_budgets_match_observed_browser_images_and_answers(case, newline: str) -> None:
    source = case["source"].replace("\n", newline)
    control = "?[%{{goal}} A | B]" if "%{{goal}}" in source else "?[{{goal}} A | B]"
    questions = [control] if case["bindings"] else []
    assert bool(list(find_document_image_labels(source))) is case["image"]
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == questions
    assert case["buttons"] == (["A", "B"] if questions else [])
    replacement = source.replace("{{goal}}", "old") if case["image"] and "%{{goal}}" not in source else source
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement
    flow = MarkdownFlow(source)
    blocks = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in blocks] == questions
    if blocks:
        assert flow.process(blocks[0].index, variables={"goal": "old"}, user_input={"goal": ["B"]}).variables == {"goal": ["B"]}


@pytest.mark.parametrize("size", [128, 512, 2048])
def test_repeated_label_tab_queries_scan_the_document_once(size: int) -> None:
    visits = 0

    class CountedSource(str):
        def __iter__(self) -> Iterator[str]:
            nonlocal visits
            for character in super().__iter__():
                visits += 1
                yield character

    source = CountedSource("text😀\ttail\t\n" * size)
    blocks = DocumentBlocks(source, COMPILED_INLINE_HTML_REGEX)
    positions = [match.start() for match in re.finditer("\t", source)]
    for _ in range(3):
        assert all(1 <= blocks.label_character_size(at) <= 4 for at in positions)
    assert visits == len(source)
