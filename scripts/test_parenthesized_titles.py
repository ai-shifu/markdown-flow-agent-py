"""Parenthesized image titles cannot contain an unescaped opening parenthesis."""

import pytest
from markdown_it import MarkdownIt

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans, find_document_protected_spans


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(("opening", "continuation"), [("", ""), ("> ", "> "), ("> - ", ">   "), ("- > ", "  > ")])
@pytest.mark.parametrize("form", ["inline", "reference", "reference-next-line"])
@pytest.mark.parametrize(
    "title",
    [
        "(Diagram)",
        "(Diagram (draft)",
        "(Diagram (draft))",
        r"(Diagram \(draft)",
        r"(Diagram \(draft\))",
        r"(Diagram \\(draft)",
        '"Diagram (draft)"',
        "'Diagram (draft)'",
        "(Diagram\n(draft)",
        "(Diagram &#40;draft&#41;)",
    ],
)
def test_parenthesized_title_admission_matches_rendering(title: str, form: str, opening: str, continuation: str, spelling: str, newline: str) -> None:
    control = "?[" + spelling + " A | B]"
    projected_title = title.replace("\n", "\n" + continuation)
    if form == "inline":
        source = opening + "![" + control + "](/x " + projected_title + ")"
    else:
        separator = " " if form == "reference" else "\n" + continuation + " "
        source = opening + "![" + control + "][image]\n\n" + opening + "[image]: /x" + separator + projected_title
    source = source.replace("\n", newline)
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


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("title", ["(Diagram (draft)", "(Diagram (draft))", "(Diagram\n(draft)"])
def test_invalid_next_line_reference_title_keeps_destination_only_fallback(title: str, newline: str) -> None:
    source = ("![?[{{goal}} A | B]][image]\n\n[image]: /x\n " + title).replace("\n", newline)
    assert "<img " in MarkdownIt().render(source)
    assert bool(list(find_document_image_labels(source)))
    assert not list(find_document_interaction_spans(source))


@pytest.mark.parametrize("image", [False, True])
@pytest.mark.parametrize("resource", ["(/x (Diagram ({{))", "(/x (Diagram \\( {{))"])
def test_parenthesized_image_validation_preserves_generic_literal_spans(resource: str, image: bool) -> None:
    prefix = ("!" if image else "") + "[example]" + resource
    source = prefix + "\n\n?[{{visible}} C | D]\n\nRead {{value}}."
    assert (prefix.index("("), len(prefix)) in list(find_document_protected_spans(source))
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ["?[{{visible}} C | D]"]
    assert replace_variables_in_text(source, {"visible": "old", "value": "current"}, add_quotes=False).endswith("Read current.")
