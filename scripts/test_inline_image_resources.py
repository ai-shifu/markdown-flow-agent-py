"""Inline image resources use paragraph text after physical container prefixes."""

import pytest
from markdown_it import MarkdownIt

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser import document_context
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(
    ("opening", "continuation"),
    [
        ("", ""),
        ("", "> "),
        ("> ", "> "),
        ("> ", ""),
        ("> ", "> > "),
        ("> - ", ">   "),
        ("> - ", "> "),
        ("- > ", "  > "),
        ("- > ", "  "),
        ("- > ", ""),
        ("1. ", "   "),
        ("1. ", ""),
        ("1. ", "2. "),
        ("> > ", "> > "),
        ("> > ", "> "),
        ("> > ", ""),
        ("> ", "   > "),
        ("> ", ">    "),
    ],
)
@pytest.mark.parametrize(
    "resource",
    [
        "(/x)",
        "(\n/x\n)",
        '(/x\n"title")',
        '(/x "one\ntwo")',
        '(/x "one\n\ntwo")',
        '(\n/x "title"\n)',
        "(\n<x>\n)",
        "(/x(a)\n 'title')",
        '(/x "a\\"b\nc")',
        '(/x "a\n# heading\nb")',
        "(\n/x\n",
        "(\n/x trailing\n)",
        "(\n\n/x\n)",
        "(\n/x\n# heading\n)",
        '(/x "a\n```\nb")',
        '(/x "a\n<!-- x -->\nb")',
        '(/x "a\n- next\nb")',
        '(/x "a\n---\nb")',
        '(/x "a\n===\nb")',
        '(/x "a\n<script>\nb")',
        '(/x "a\n<div>\nb")',
        '(/x "a\n<custom>\nb")',
    ],
)
def test_inline_image_resource_admission_matches_rendering(opening: str, continuation: str, resource: str, spelling: str, newline: str) -> None:
    """Only complete images within one paragraph can hide an alternative-text control."""
    control = "?[" + spelling + " A | B]"
    source = (opening + "![" + control + "]" + resource.replace("\n", "\n" + continuation)).replace("\n", newline)
    image = "<img " in MarkdownIt().render(source)
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ([] if image else [control])
    replacement = source.replace("{{goal}}", "old") if image and spelling == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement
    # Single-line comments are intentionally removed by MarkdownFlow preprocessing.
    if "<!-- x -->" not in resource:
        flow = MarkdownFlow(source)
        questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
        assert [block.content for block in questions] == ([] if image else [control])
        if questions:
            assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["A"]}).variables == {"goal": ["A"]}


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize(
    "image",
    [
        "> ![?[{{goal}} A | B]](\n> /x\n> )",
        '> ![?[{{goal}} A | B]](/x\n> "title")',
        '> - ![?[{{goal}} A | B]](/x "one\n>   two")',
        "- > ![?[{{goal}} A | B]](\n  > /x\n  > )",
        '> > ![?[{{goal}} A | B]](/x "one\n> two")',
        '> ![?[{{goal}} A | B]](/x "one\n===\ntwo")',
    ],
)
def test_multiline_image_alt_keeps_memory_references_and_following_answers(image: str, newline: str) -> None:
    """Real images substitute content references and leave following question bindings intact."""
    image = image.replace("\n", newline)
    source = image + newline * 2 + "Read {{goal}}." + newline * 2 + "?[{{visible}} C | D]"
    assert "<img " in MarkdownIt().render(image)
    assert replace_variables_in_text(source, {"goal": "current", "visible": "old"}, add_quotes=False) == source.replace("{{goal}}", "current")
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ["?[{{visible}} C | D]"]
    assert flow.process(questions[0].index, variables={"visible": "old"}, user_input={"visible": ["D"]}).variables == {"visible": ["D"]}


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(
    ("prefix", "opening", "continuation", "image"),
    [
        ("> prefix\n", "", "", True),
        ("> - prefix\n", "> ", "> ", True),
        ("- > prefix\n", "  ", "  ", True),
        ("prefix\n", "", "", False),
        ("> # heading\n", "", "", False),
        ("> <!-- x -->\n", "", "", False),
    ],
)
def test_inline_resources_follow_the_owning_paragraph_after_lazy_lines(prefix: str, opening: str, continuation: str, image: bool, spelling: str, newline: str) -> None:
    control = "?[" + spelling + " A | B]"
    source = (prefix + opening + "![" + control + '](/x "a\n' + continuation + "===\n" + continuation + 'b")').replace("\n", newline)
    assert ("<img " in MarkdownIt().render(source)) is image
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ([] if image else [control])


@pytest.mark.parametrize("size", [100, 200, 400])
def test_resource_boundaries_reuse_lazy_suffixes_without_repeated_scans(monkeypatch: pytest.MonkeyPatch, size: int) -> None:
    calls = 0
    original = document_context.container_content_start

    def counted(line: str, steps: tuple[int, ...], *, partial: bool = False) -> int | None:
        nonlocal calls
        calls += 1
        return original(line, steps, partial=partial)

    monkeypatch.setattr(document_context, "container_content_start", counted)
    source = "> " + "![image](/x) " * size + "\n" + "===\n" * size + "tail"
    assert MarkdownIt().render(source).count("<img ") == size
    assert len(list(find_document_image_labels(source))) == size
    assert calls <= 4 * size


def test_comment_preprocessing_keeps_its_existing_inline_title_behavior() -> None:
    source = '![?[{{goal}} A | B]](/x "a\n<!-- x -->\nb")'
    assert "<img " not in MarkdownIt().render(source)
    flow = MarkdownFlow(source)
    assert "<img " in MarkdownIt().render(flow.get_processed_document())
    assert all(block.block_type != BlockType.INTERACTION for block in flow.get_all_blocks())


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("html", ["<div>", "</div>", "<table>", "<custom>"])
@pytest.mark.parametrize(("prefix", "continuation"), [("> ", ""), ("> - ", "> "), ("- > ", "  "), ("> > ", "> "), ("- ", "")])
@pytest.mark.parametrize("text", ["1.", "2. next"])
def test_inline_image_owner_restarts_after_ordinary_html_dedent(prefix: str, continuation: str, html: str, text: str, spelling: str, newline: str) -> None:
    """An HTML block's exited container cannot turn root title text into a fresh item."""
    control = "?[" + spelling + " A | B]"
    source = (prefix + html + "\n" + continuation + "![" + control + '](/x "a\n' + continuation + text + "\n" + continuation + 'b")').replace("\n", newline)
    image = "<img " in MarkdownIt().render(source)
    assert image
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ([] if image else [control])
    replacement = source.replace("{{goal}}", "old") if image and spelling == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement
    assert [block.content for block in MarkdownFlow(source).get_all_blocks() if block.block_type == BlockType.INTERACTION] == ([] if image else [control])


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("html", ["<div>", "<custom>"])
@pytest.mark.parametrize("body", ["> body", "> - body"])
def test_quoted_blank_ends_html_before_the_next_image_paragraph(html: str, body: str, spelling: str, newline: str) -> None:
    control = "?[" + spelling + " A | B]"
    source = ("> " + html + "\n" + body + "\n>\n> ![" + control + '](/x "a\n> 1.\n> b")').replace("\n", newline)
    assert "<img " in MarkdownIt().render(source)
    assert bool(list(find_document_image_labels(source)))
    assert not list(find_document_interaction_spans(source))
    assert all(block.block_type != BlockType.INTERACTION for block in MarkdownFlow(source).get_all_blocks())
