"""Fresh reference definitions follow confirmed block closures and retain literal fallback."""

import pytest
from markdown_it import MarkdownIt

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans, find_document_protected_spans


def _assert_image_contract(source: str, spelling: str, *, check_flow: bool = True) -> None:
    control = "?[" + spelling + " A | B]"
    image = "<img " in MarkdownIt().render(source)
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ([] if image else [control])
    replacement = source.replace("{{goal}}", "old") if image and spelling == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement
    if not check_flow:
        return
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ([] if image else [control])
    if questions:
        assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["A"]}).variables == {"goal": ["A"]}


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(("opening", "continuation"), [("", ""), ("> ", "> "), ("- ", "  "), ("> - ", ">   ")])
@pytest.mark.parametrize(
    ("body", "expected_image"),
    [
        ("<!-- x -->", True),
        ("<!-- x\n2. raw\n-->", True),
        ("<!-->", True),
        ("<!--->", True),
        ("<?instruction?>", True),
        ("<?instruction\n?>", True),
        ("<![CDATA[x]]>", True),
        ("<![CDATA[\n]]>", True),
        ("<!DOCTYPE x>", True),
        ("<script>x</script>", True),
        ("<style>\n2. raw\n</style>", True),
        ("<pre>\nraw\n</pre>", True),
        ("<textarea>\nraw\n</textarea>", True),
        ("    code", True),
        ("    code\n    more", True),
        ("\tcode", True),
        ("Heading\n===", True),
        ("Heading\n---", True),
        ("```\n2. code\n```", True),
        ("~~~\n2. code\n~~~", True),
        ("paragraph\n    continuation", False),
        ("paragraph\n\tcontinuation", False),
        ("paragraph\n<span>", False),
        ("paragraph\n</script>", False),
        ("<div>\nraw\n</div>", False),
        ("<span>\nraw\n</span>", False),
        ("<!-- incomplete", False),
        ("<script>incomplete", False),
        ("```\nincomplete", False),
        ("Heading\n2. continuation", False),
    ],
)
def test_fresh_ordered_items_follow_confirmed_nonparagraph_blocks(body: str, expected_image: bool, opening: str, continuation: str, spelling: str, newline: str) -> None:
    """Only real closed blocks allow a fresh ordered list inside the same container."""
    lines = body.split("\n")
    prefix = opening + lines[0] + "\n" + "".join(continuation + line + "\n" for line in lines[1:])
    source = ("![?[" + spelling + " A | B]][image]\n\n" + prefix + continuation + "2. [image]: /x").replace("\n", newline)
    if not opening:
        assert ("<img " in MarkdownIt().render(source)) is expected_image
    # MarkdownFlow uses --- as a document separator rather than a setext heading.
    _assert_image_contract(source, spelling, check_flow=body != "Heading\n---")


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("html", ["<!-- incomplete", "<?incomplete", "<![CDATA[incomplete", "<!DOCTYPE incomplete"])
@pytest.mark.parametrize("marker", ["1. ", "- "])
@pytest.mark.parametrize(("opening", "continuation"), [("", ""), ("> ", "> "), ("- ", "  "), ("> - ", ">   ")])
def test_unterminated_html_cannot_define_an_image_reference(html: str, marker: str, opening: str, continuation: str, spelling: str, newline: str) -> None:
    """Image confirmation does not promote a definition from unfinished HTML."""
    source = ("![?[" + spelling + " A | B]][image]\n\n" + opening + html + "\n" + continuation + marker + "[image]: /x").replace("\n", newline)
    assert "<img " not in MarkdownIt().render(source)
    _assert_image_contract(source, spelling)


@pytest.mark.parametrize("html", ["<!-- incomplete", "<?incomplete", "<![CDATA[incomplete", "<!DOCTYPE incomplete"])
def test_unterminated_html_keeps_generic_reference_literal_fallback(html: str) -> None:
    """Only the image inventory changes; generic reference resources stay protected."""
    definition = "1. [image]: /x"
    source = html + "\n" + definition
    spans = [source[start:end] for start, end in find_document_protected_spans(source)]
    assert definition in spans


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("heading", ["Heading\n===", "# heading"])
def test_heading_list_dedent_does_not_create_a_code_definition(heading: str, spelling: str, newline: str) -> None:
    """An indented line after a root heading is code after a preceding list exits."""
    source = ("![?[" + spelling + " A | B]][image]\n\n- text\n" + heading + "\n    [image]: /x").replace("\n", newline)
    assert "<img " not in MarkdownIt().render(source)
    _assert_image_contract(source, spelling)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("html", ["<!-- incomplete", "<?incomplete", "<![CDATA[incomplete", "<!DOCTYPE incomplete"])
@pytest.mark.parametrize("image", ["![{control}](/x)", "![{control}][image]", "{control}"])
def test_unterminated_html_does_not_promote_an_image_boundary(html: str, image: str, spelling: str, newline: str) -> None:
    """The historical visible-control fallback remains even for image-looking source."""
    control = "?[" + spelling + " A | B]"
    source = ("[image]: /x\n\n" + html + "\n" + image.format(control=control)).replace("\n", newline)
    assert "<img " not in MarkdownIt().render(source)
    _assert_image_contract(source, spelling)


@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("html", ["<!doctype x", "<!z x", "<![cdata[x", "< !-- x"])
def test_only_native_html_openers_limit_image_admission(html: str, spelling: str) -> None:
    source = "![?[" + spelling + " A | B]][image]\n\n" + html + "\n1. [image]: /x"
    assert "<img " in MarkdownIt().render(source)
    _assert_image_contract(source, spelling)


@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(
    "prefix",
    [
        "[image]: /x\n\n<!-- incomplete\n1. [other]: /other",
        "```\n<!-- incomplete\n```\n2. [image]: /x",
        "<pre>\n<!-- incomplete\n</pre>\n2. [image]: /x",
        "> <!-- incomplete\n2. [image]: /x",
    ],
)
def test_unterminated_html_metadata_stays_inside_its_real_block(prefix: str, spelling: str) -> None:
    source = "![?[" + spelling + " A | B]][image]\n\n" + prefix
    assert "<img " in MarkdownIt().render(source)
    _assert_image_contract(source, spelling)


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_flow_document_separators_keep_image_references_local(newline: str) -> None:
    """MarkdownFlow's explicit document separator keeps its existing segment contract."""
    source = "![?[{{goal}} A | B]][image]\n\nHeading\n---\n2. [image]: /x".replace("\n", newline)
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ["?[{{goal}} A | B]"]
