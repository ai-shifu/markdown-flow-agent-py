"""Preserved-output admission and extraction keep opaque marker text atomic."""

import pytest

from markdown_flow import MarkdownFlow
from markdown_flow.enums import BlockType
from markdown_flow.parser.output import extract_preserved_content, is_preserved_content_block


KEYS = ["===title===", "!===", "a===b===c", "a!===b!===c", "quotes'\\===b===}", "nested{{===title==="]


def _wrap(reference: str, style: str) -> str:
    return "===" + reference + "===" if style == "inline" else "!===\n" + reference + "\n!==="


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("style", ["inline", "fenced"])
@pytest.mark.parametrize("padding", [" ", "\n", "\r\n", "\x85"])
def test_preserved_only_processing_keeps_the_exact_name(key: str, style: str, padding: str) -> None:
    reference = "{{" + padding + key + padding + "}}"
    source = " \t\n" + _wrap(reference, style) + "\n \t"
    values: dict[str, str | list[str]] = {key: "VALUE"}
    assert is_preserved_content_block(source)
    assert extract_preserved_content(source) == reference
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == [key]
    assert flow.get_block(0).block_type == BlockType.PRESERVED_CONTENT
    assert [result.content for result in flow.process(0, variables=values)] == ["VALUE"]
    user = flow.get_content_messages(0, values)[-1]["content"]
    assert "VALUE" in user
    assert "UNKNOWN" not in user
    assert values == {key: "VALUE"}


@pytest.mark.parametrize("value", ["===VALUE===", "!===VALUE!===", "quotes'\\VALUE}"])
def test_preserved_values_are_not_reinterpreted_as_output_operators(value: str) -> None:
    source = "!===\n{{\n===title===\n}}\n!==="
    flow = MarkdownFlow(source)
    assert [result.content for result in flow.process(0, variables={"===title===": value})] == [value]
    assert value in flow.get_content_messages(0, {"===title===": value})[-1]["content"]


@pytest.mark.parametrize(("source", "expected"), [("===one===", "one"), ("!===\n one \n!===", " one "), ("===one===\n!===\ntwo\n!===", "one\ntwo")])
def test_existing_preserved_output_formats_keep_their_original_behavior(source: str, expected: str) -> None:
    assert is_preserved_content_block(source)
    assert extract_preserved_content(source) == expected
    assert "".join(result.content for result in MarkdownFlow(source).process(0)) == expected


@pytest.mark.parametrize("reference", ["{{bad===name===\ninvalid}}", "{{x{{===name===}}"])
def test_invalid_and_first_closing_pair_markers_remain_atomic(reference: str) -> None:
    source = _wrap(reference, "fenced")
    assert is_preserved_content_block(source)
    assert extract_preserved_content(source) == reference


def test_preserved_extraction_keeps_a_genuinely_unfinished_tail_atomic() -> None:
    tail = "{{unfinished\n===not an operator===\n!==="
    source = "!===\n" + tail
    assert not is_preserved_content_block(source)
    assert extract_preserved_content(source) == tail


def test_escaped_document_openers_keep_existing_operator_behavior() -> None:
    source = "!===\n\\{{\n===title===\n}}\n!==="
    assert is_preserved_content_block(source)
    assert extract_preserved_content(source) == "\\{{\ntitle\n}}"


def test_public_preserved_consumers_share_collision_free_marker_restoration() -> None:
    reference = "{{\n===title===\n}}"
    literal = "\x00mdf-output-name:0:0\x00"
    source = _wrap(literal + "\n" + reference, "fenced")
    assert is_preserved_content_block(source)
    assert extract_preserved_content(source) == literal + "\n" + reference


@pytest.mark.parametrize("key", KEYS)
def test_operator_text_inside_a_name_alone_is_not_preserved_output(key: str) -> None:
    assert not is_preserved_content_block("{{ " + key + " }}")
