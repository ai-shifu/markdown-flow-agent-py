"""Image confirmation uses the renderer's default URL policy without changing literals."""

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
def test_only_renderer_eligible_inline_images_hide_alt_controls(destination: str, opening: str, continuation: str, angle: bool, spelling: str, newline: str) -> None:
    resource = "<" + destination + ">" if angle else destination
    control = "?[" + spelling + " A | B]"
    source = (opening + "![" + control + "](\n" + continuation + resource + "\n" + continuation + ")").replace("\n", newline)
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


@pytest.mark.parametrize("angle", [False, True])
@pytest.mark.parametrize("destination", ["javascript:alert", "data:image/svg+xml;base64,abc"])
def test_rejected_images_keep_their_named_answer_fresh(destination: str, angle: bool) -> None:
    resource = "<" + destination + ">" if angle else destination
    source = "![?[{{goal}} A | B]](" + resource + ")"
    assert "<img " not in MarkdownIt().render(source)
    assert replace_variables_in_text(source, {"goal": "stale"}, add_quotes=False) == source
    question = next(block for block in MarkdownFlow(source).get_all_blocks() if block.block_type == BlockType.INTERACTION)
    assert MarkdownFlow(source).process(question.index, variables={"goal": "stale"}, user_input={"goal": ["B"]}).variables == {"goal": ["B"]}


@pytest.mark.parametrize("image", [False, True])
@pytest.mark.parametrize("resource", ['(javascript:alert "{{")', '(javascript\\:alert "{{")', '(data:image/svg+xml;base64,abc "{{")', '(<javascript:alert> "{{")'])
def test_image_url_policy_preserves_generic_resource_literal_spans(resource: str, image: bool) -> None:
    prefix = ("!" if image else "") + "[example]" + resource
    source = prefix + "\n\n?[{{visible}} C | D]\n\nRead {{value}}."
    assert (prefix.index("("), len(prefix)) in list(find_document_protected_spans(source))
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ["?[{{visible}} C | D]"]
    assert replace_variables_in_text(source, {"value": "current", "visible": "old"}, add_quotes=False).endswith("Read current.")
