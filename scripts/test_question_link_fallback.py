"""Disqualified question candidates retain native link-resource boundaries."""

import pytest

from markdown_flow import InteractionParser, MarkdownFlow, extract_variables_from_text, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import find_document_interaction_spans


QUESTION = "?[%{{ real }} A|B]"
LINKS = [
    "?[Label](dest/{{unfinished)",
    "?[Label](<dest/{{unfinished>)",
    '?[Label](dest "{{unfinished")',
    "?[Label](dest '{{unfinished')",
    "?[Label](dest ({{unfinished))",
    "?[Label](d(n)/{{unfinished)",
]


def _interactions(source: str) -> list[str]:
    return [block.content for block in MarkdownFlow(source).get_all_blocks() if block.block_type == BlockType.INTERACTION]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("link", LINKS)
def test_disqualified_question_replays_its_native_link_label(link: str, newline: str) -> None:
    prefix = link + newline * 2
    source = prefix + QUESTION
    assert extract_variables_from_text(source) == ["real"]
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == ["real"]
    assert _interactions(source) == [QUESTION]
    block = next(block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION)
    assert flow.process(block.index, user_input={"real": ["B"]}).variables == {"real": ["B"]}
    assert list(find_document_interaction_spans(source)) == [(len(prefix), len(source))]
    assert replace_variables_in_text(prefix + "{{ real }}", {"real": "VALUE"}, add_quotes=False) == prefix + "VALUE"


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("link", ["?[Label](dest/{{unfinished", "?[outer [inner](u)](dest/{{unfinished)"])
def test_incomplete_or_inactive_resources_keep_raw_marker_ownership(link: str, newline: str) -> None:
    source = link + newline * 2 + QUESTION
    assert extract_variables_from_text(source) == []
    assert MarkdownFlow(source).extract_variables() == []
    assert QUESTION not in _interactions(source)
    assert replace_variables_in_text(source, {"real": "VALUE"}, add_quotes=False) == source


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_replayed_labels_and_resources_keep_complete_names_exact(newline: str) -> None:
    prefix = "?[{{ a]b }}](dest/{{ value ? }})" + newline * 2
    source = prefix + QUESTION
    assert set(extract_variables_from_text(source)) == {"a]b", "value ?", "real"}
    assert set(MarkdownFlow(source).extract_variables()) == {"a]b", "value ?", "real"}
    assert _interactions(source) == [QUESTION]
    assert replace_variables_in_text(source, {"a]b": "LABEL", "value ?": "DEST"}, add_quotes=False) == "?[LABEL](dest/DEST)" + newline * 2 + QUESTION


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_only_an_adjacent_parenthesis_disqualifies_the_existing_control(newline: str) -> None:
    source = "?[Label] (dest/{{unfinished)" + newline * 2 + QUESTION
    assert _interactions(source) == ["?[Label]"]
    assert extract_variables_from_text(source) == []


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_marker_body_closing_brackets_do_not_trigger_link_fallback(newline: str) -> None:
    first = "?[%{{ a](b }} A|B]"
    source = first + newline * 2 + QUESTION
    assert _interactions(source) == [first, QUESTION]
    assert InteractionParser().parse(first)["variable"] == "a](b"
    assert set(extract_variables_from_text(source)) == {"a](b", "real"}


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_a_marker_opened_inside_the_candidate_stays_atomic(newline: str) -> None:
    source = "?[{{unfinished](dest)" + newline * 2 + QUESTION
    assert extract_variables_from_text(source) == []
    assert _interactions(source) == [source]
