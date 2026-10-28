"""Multiline reference definitions keep image alt text outside interactive controls."""

import pytest

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("prefix", ["", "%"])
@pytest.mark.parametrize(
    "definition",
    [
        "[course\nimage]: /diagram.png",
        "[course\n   image]: /diagram.png",
        "[course\n    image]: /diagram.png",
        "> [course\n> image]: /diagram.png",
        "> [course\nimage]: /diagram.png",
        "- [course\n  image]: /diagram.png",
        "[course\nimage]:\n /diagram.png",
        '[course\nimage]: /diagram.png "Title"',
    ],
)
def test_multiline_reference_image_does_not_create_a_question(newline, prefix, definition):
    image = "![?[" + prefix + "{{goal}} A | B]][course image]"
    source = (image + "\n\n" + definition + "\n\n?[{{real}} C | D]").replace("\n", newline)
    assert list(find_document_image_labels(source)) == [(1, len(image.split("][course image]")[0]) + 1)]
    controls = list(find_document_interaction_spans(source))
    assert [source[start:end] for start, end in controls] == ["?[{{real}} C | D]"]
    replaced = replace_variables_in_text(source, {"goal": "old", "real": "stale"}, add_quotes=False)
    expected = source if prefix else source.replace("{{goal}}", "old")
    assert replaced == expected
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ["?[{{real}} C | D]"]
    assert flow.process(questions[0].index, user_input={"real": ["C"]}).variables == {"real": ["C"]}


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize(
    "definition",
    [
        "[course\n\nimage]: /diagram.png",
        "[course\nimage] /diagram.png",
        "[course\n[image]: /diagram.png",
        "[course\n# image]: /diagram.png",
        "[course\n```\nimage]: /diagram.png",
        "    [course\n    image]: /diagram.png",
        "```md\n[course\nimage]: /diagram.png\n```",
        '[course\nimage]: /diagram.png "Unterminated',
        "[course\nimage]: /diagram.png trailing",
        "[other\nimage]: /diagram.png",
        "{{ outer\n\n[course\nimage]: /diagram.png\n}}",
    ],
)
def test_invalid_or_opaque_reference_definition_does_not_hide_a_real_question(newline, definition):
    source = ("![?[{{goal}} A | B]][course image]\n\n" + definition).replace("\n", newline)
    assert list(find_document_image_labels(source)) == []
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == source
    controls = list(find_document_interaction_spans(source))
    assert [source[start:end] for start, end in controls] == ["?[{{goal}} A | B]"]


@pytest.mark.parametrize("key", ["Which [path] | level//hint...?", "outer{{inner", "a}", "path\\"])
def test_multiline_reference_resolution_preserves_opaque_marker_names(key):
    image = "![?[{{ " + key + " }} A | B]][course image]"
    source = image + "\n\n[course\nimage]: /diagram.png\n\n?[{{ " + key + " }} C | D]"
    assert replace_variables_in_text(source, {key: "old"}, add_quotes=False) == (image.replace("{{ " + key + " }}", "old") + "\n\n[course\nimage]: /diagram.png\n\n?[{{ " + key + " }} C | D]")
    questions = [block for block in MarkdownFlow(source).get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert len(questions) == 1
    flow = MarkdownFlow(source)
    assert flow.process(questions[0].index, user_input={key: ["D"]}).variables == {key: ["D"]}
