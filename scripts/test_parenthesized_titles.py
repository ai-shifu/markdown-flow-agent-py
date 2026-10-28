"""Image-title admission follows captured browser behavior, not another parser's rules."""

import json
from pathlib import Path

import pytest

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans, find_document_protected_spans


OBSERVED_CASES = json.loads(Path(__file__).with_name("parenthesized-title-observed-cases.json").read_text())["cases"]


@pytest.mark.parametrize("case", OBSERVED_CASES, ids=lambda case: str(case["id"]))
def test_parenthesized_titles_match_observed_images_and_visible_questions(case) -> None:
    source = case["source"]
    observed = case["observed"]
    image = bool(observed["images"])
    questions = []
    if "A" in observed["buttons"]:
        questions.append("?[" + case["marker"] + " A | B]")
    if "C" in observed["buttons"]:
        questions.append("?[{{visible}} C | D]")
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == questions
    replacement = source.replace("{{goal}}", "old") if image and case["marker"] == "{{goal}}" else source
    variables: dict[str, str | list[str]] = {"goal": "old", "visible": "stale", "inside": "{{inside}}"}
    assert replace_variables_in_text(source, variables, add_quotes=False) == replacement
    flow = MarkdownFlow(source)
    blocks = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in blocks] == questions
    for block in blocks:
        name, value = ("visible", "D") if block.content == "?[{{visible}} C | D]" else ("goal", "B")
        assert flow.process(block.index, variables=variables, user_input={name: [value]}).variables == {name: [value]}


@pytest.mark.parametrize("image", [False, True])
@pytest.mark.parametrize("resource", ["(/x (Diagram ({{))", "(/x (Diagram \\( {{))"])
def test_parenthesized_resources_preserve_generic_literal_spans(resource: str, image: bool) -> None:
    prefix = ("!" if image else "") + "[example]" + resource
    source = prefix + "\n\n?[{{visible}} C | D]\n\nRead {{value}}."
    assert (prefix.index("("), len(prefix)) in list(find_document_protected_spans(source))
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ["?[{{visible}} C | D]"]
    assert replace_variables_in_text(source, {"visible": "old", "value": "current"}, add_quotes=False).endswith("Read current.")
