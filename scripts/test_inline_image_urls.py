"""Image nodes hide their alt controls even when the renderer sanitizes their URL."""

from unittest.mock import patch

import pytest
from markdown_it import MarkdownIt

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans, find_document_protected_spans


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("angle", [False, True])
@pytest.mark.parametrize(("opening", "continuation"), [("", ""), ("> ", "> "), ("> - ", ">   "), ("- > ", "  > ")])
@pytest.mark.parametrize(
    "destination",
    [
        "/x",
        "https://example.com/image.png",
        "//example.com/x",
        "mailto:a@example.com",
        "http://example.com/x",
        "javascript:alert",
        "JaVaScRiPt:alert",
        "java&#x73;cript:alert",
        r"javascript\:alert",
        "&#106;avascript:alert",
        "vbscript:alert",
        "file:///x",
        "data:text/plain,hello",
        "data:image/svg+xml;base64,abc",
        "data:image/svg+xml;base64,PHN2Zy8+",
        "data:image/png;base64,abc",
        "data:image/gif;base64,abc",
        "data:image/jpeg;base64,abc",
        "data:image/webp;base64,abc",
        "DATA:IMAGE/PNG;base64,abc",
        "java%73cript:alert",
        "javascript&colon;alert",
        "data&colon;image/svg+xml;base64,abc",
        "",
        "urn:asset:image",
    ],
)
def test_syntactic_inline_images_hide_alt_controls_before_url_sanitization(destination: str, opening: str, continuation: str, angle: bool, spelling: str, newline: str) -> None:
    resource = "<" + destination + ">" if angle else destination
    control = "?[" + spelling + " A | B]"
    source = (opening + "![" + control + "](\n" + continuation + resource + "\n" + continuation + ")").replace("\n", newline)
    renderer = MarkdownIt()
    # The browser creates the image node before sanitizing its URL. MarkdownIt's
    # default scheme filter instead rejects the node, so use its syntax alone.
    with patch.object(renderer, "validateLink", return_value=True):
        image = "<img " in renderer.render(source)
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ([] if image else [control])
    replacement = source.replace("{{goal}}", "old") if image and spelling == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ([] if image else [control])
    if questions:
        assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["A"]}).variables == {"goal": ["A"]}


@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("angle", [False, True])
@pytest.mark.parametrize("form", ["inline", "reference"])
@pytest.mark.parametrize("destination", ["javascript:alert", "data:image/svg+xml;base64,PHN2Zy8+", "data:text/html,hello", "vbscript:alert", "file:///x"])
def test_sanitized_image_nodes_preserve_old_values_and_the_following_real_answer(destination: str, form: str, angle: bool, spelling: str) -> None:
    resource = "<" + destination + ">" if angle else destination
    image = "![?[" + spelling + " A | B]]"
    source = image + "(" + resource + ")" if form == "inline" else image + "[image]\n\n[image]: " + resource
    source += "\n\n?[{{visible}} C | D]"
    assert list(find_document_image_labels(source))
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ["?[{{visible}} C | D]"]
    replacement = source.replace("{{goal}}", "stale") if spelling == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "stale", "visible": "old"}, add_quotes=False) == replacement
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ["?[{{visible}} C | D]"]
    assert flow.process(questions[0].index, variables={"goal": "stale", "visible": "old"}, user_input={"visible": ["D"]}).variables == {"visible": ["D"]}


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("angle", [False, True])
@pytest.mark.parametrize("slashes", [1, 2, 3])
@pytest.mark.parametrize(("opening", "continuation"), [("", ""), ("> ", "> ")])
def test_physical_destination_newlines_keep_the_real_named_question(newline: str, spelling: str, angle: bool, slashes: int, opening: str, continuation: str) -> None:
    destination = "/diagram" + "\\" * slashes + newline + continuation + ".png"
    resource = "<" + destination + ">" if angle else destination
    control = "?[" + spelling + " A | B]"
    source = opening + "![" + control + "](" + resource + ")"
    assert not list(find_document_image_labels(source))
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == [control]
    assert replace_variables_in_text(source, {"goal": "stale"}, add_quotes=False) == source
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == [control]
    assert flow.process(questions[0].index, variables={"goal": "stale"}, user_input={"goal": ["B"]}).variables == {"goal": ["B"]}


@pytest.mark.parametrize("image", [False, True])
@pytest.mark.parametrize("resource", ['(javascript:alert "{{")', '(javascript\\:alert "{{")', '(data:image/svg+xml;base64,abc "{{")', '(<javascript:alert> "{{")'])
def test_image_url_policy_preserves_generic_resource_literal_spans(resource: str, image: bool) -> None:
    prefix = ("!" if image else "") + "[example]" + resource
    source = prefix + "\n\n?[{{visible}} C | D]\n\nRead {{value}}."
    assert (prefix.index("("), len(prefix)) in list(find_document_protected_spans(source))
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ["?[{{visible}} C | D]"]
    assert replace_variables_in_text(source, {"value": "current", "visible": "old"}, add_quotes=False).endswith("Read current.")
