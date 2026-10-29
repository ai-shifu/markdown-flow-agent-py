"""Thematic breaks retain image-definition boundaries inside and outside lists."""

import re
from types import SimpleNamespace

import pytest
from markdown_it import MarkdownIt

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser import document_blocks
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("rule", ["* * *", "- - -", "_ _ _"])
@pytest.mark.parametrize(
    "body",
    [
        "{rule}\n[image]: /x",
        "paragraph\n{rule}\n[image]: /x",
        "- text\n  {rule}\n    [image]: /x",
        "- text\n{rule}\n    [image]: /x",
        "> {rule}\n> [image]: /x",
        "> - text\n>   {rule}\n>     [image]: /x",
        "- > {rule}\n  [image]: /x",
        "- > {rule}\n    [image]: /x",
        "    {rule}\n[image]: /x",
    ],
)
def test_thematic_breaks_follow_renderer_container_boundaries(body: str, rule: str, spelling: str, newline: str) -> None:
    """A thematic rule closes its real container without creating nested empty lists."""
    control = "?[" + spelling + " A | B]"
    source = ("![" + control + "][image]\n\n" + body.format(rule=rule)).replace("\n", newline)
    image = "<img " in MarkdownIt().render(source)
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ([] if image else [control])
    replacement = source.replace("{{goal}}", "old") if image and spelling == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ([] if image else [control])
    if questions:
        assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["A"]}).variables == {"goal": ["A"]}


@pytest.mark.parametrize("depth", [256, 1024, 4096])
def test_thematic_precedence_does_not_rescan_each_nested_list_tail(monkeypatch: pytest.MonkeyPatch, depth: int) -> None:
    """Long non-thematic lists must retain a bounded amount of suffix matching."""
    work = 0
    original = document_blocks.COMPILED_DOCUMENT_BREAK_REGEX

    def counted(value: str) -> re.Match[str] | None:
        nonlocal work
        work += len(value)
        return original.fullmatch(value)

    monkeypatch.setattr(document_blocks, "COMPILED_DOCUMENT_BREAK_REGEX", SimpleNamespace(fullmatch=counted))
    source = "- " * depth + "paragraph"
    content, steps, _ = document_blocks.container_opening_info(source)
    assert source[content:] == "paragraph"
    assert steps == (2,) * depth
    assert work <= 4 * len(source)
