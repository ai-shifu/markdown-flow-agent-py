"""Only native block-start reference definitions can classify an image label."""

import pytest
from markdown_it import MarkdownIt

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans


@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("marker", ["", "1. ", "2. ", "9. ", "- ", "* ", "2) "])
@pytest.mark.parametrize("outer", ["", "> ", "  ", "   ", "    "])
@pytest.mark.parametrize("prefix", ["text", "1. text", "8. text", "- text", "> text", "> 1. text", "- 1. text", "1.\n   text"])
def test_container_transitions_follow_the_renderer_reference_boundary(prefix: str, outer: str, marker: str, spelling: str) -> None:
    """Later siblings start blocks, while root and nested lazy paragraphs do not."""
    control = "?[" + spelling + " A | B]"
    source = "![" + control + "][image]\n\n" + prefix + "\n" + outer + marker + "[image]: /x"
    image = "<img " in MarkdownIt().render(source)
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ([] if image else [control])
    replacement = source.replace("{{goal}}", "old") if image and spelling == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("multiline", [False, True])
@pytest.mark.parametrize(
    ("prefix", "opening", "continuation"),
    [
        pytest.param("1. text", "2. ", "   ", id="ordered-sibling"),
        pytest.param("8. text", "9. ", "   ", id="later-ordered-sibling"),
        pytest.param("- text", "2. ", "   ", id="bullet-to-ordered"),
        pytest.param("1. text", "2) ", "   ", id="ordered-delimiter-change"),
        pytest.param("> text", "2. ", "   ", id="quote-exit"),
        pytest.param("> 1. text", "> 2. ", ">    ", id="quoted-ordered-sibling"),
        pytest.param("- 1. text", "  2. ", "     ", id="nested-ordered-sibling"),
        pytest.param("1.\n   text", "2. ", "   ", id="empty-first-item"),
        pytest.param("1.   \n   text", "2. ", "   ", id="padded-empty-first-item"),
        pytest.param("prose", "2. ", "   ", id="root-lazy-paragraph"),
        pytest.param("1. text\n   prose", "   2. ", "      ", id="nested-lazy-paragraph"),
        pytest.param("> 1. text", "> ", "> ", id="quote-list-lazy-paragraph"),
    ],
)
def test_container_reference_boundaries_keep_real_flow_answers(prefix: str, opening: str, continuation: str, multiline: bool, spelling: str, newline: str) -> None:
    """Block splitting and named answers agree with single and multiline image references."""
    control = "?[" + spelling + " A | B]"
    definition = opening + ("[course\n" + continuation + "image]: /x" if multiline else "[course image]: /x")
    source = ("![" + control + "][course image]\n\n" + prefix + "\n" + definition).replace("\n", newline)
    image = "<img " in MarkdownIt().render(source)
    assert bool(list(find_document_image_labels(source))) is image
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ([] if image else [control])
    replacement = source.replace("{{goal}}", "old") if image and spelling == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement
    if questions:
        assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["A"]}).variables == {"goal": ["A"]}


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(
    ("definition", "image"),
    [
        ("1. text\n2. [course\nimage]: /x", True),
        ("> 1. text\n> 2. [course\n> image]: /x", True),
        ("- > 1. text\n  > 2. [course\n  > image]: /x", True),
        ("1. text\n   1. nested\n   2. [course\n   image]: /x", True),
        ("> 1. text\n> 2. [course image]:\n> /x", True),
        ("> 1. text\n> [course\n> image]: /x", False),
        ("1. text\n   paragraph\n   2. [course\n   image]: /x", False),
        ("paragraph\n2. [course\nimage]: /x", False),
        ("1.\n   text\n2. [course image]: /x", True),
        ("1.   \n   text\n2. [course image]: /x", True),
        ("1.\n\n   text\n2. [course image]: /x", False),
        ("> 1.\n>\n> text\n> 2. [course image]: /x", False),
    ],
)
def test_partial_container_references_and_empty_items_preserve_visible_controls(definition: str, image: bool, spelling: str, newline: str) -> None:
    """Lazy reference continuations retain outer quotes and empty items close on blanks."""
    control = "?[" + spelling + " A | B]"
    source = ("![" + control + "][course image]\n\n" + definition).replace("\n", newline)
    assert ("<img " in MarkdownIt().render(source)) is image
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ([] if image else [control])
    replacement = source.replace("{{goal}}", "old") if image and spelling == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement


@pytest.mark.parametrize("multiline", [False, True])
@pytest.mark.parametrize(
    ("prefix", "container"),
    [
        pytest.param("paragraph\n", "", id="paragraph"),
        pytest.param("paragraph\n\n", "", id="blank"),
        pytest.param("[one]: /one\n", "", id="adjacent-definition"),
        pytest.param("[one]: /one\n[two]: /two\n", "", id="consecutive-definitions"),
        pytest.param('[one]: /one\n "title"\n', "", id="definition-title"),
        pytest.param("[one]: /one invalid\n", "", id="failed-definition"),
        pytest.param("[one]: /one\nparagraph\n", "", id="paragraph-after-definition"),
        pytest.param("# heading\n", "", id="heading"),
        pytest.param("Heading\n===\n", "", id="setext"),
        pytest.param("---\n", "", id="thematic"),
        pytest.param("```\ncode\n```\n", "", id="fence"),
        pytest.param("    code\n", "", id="indented-code"),
        pytest.param("    code\n    more\n", "", id="multiline-indented-code"),
        pytest.param("<script>raw</script>\n", "", id="raw-html"),
        pytest.param("<!-- comment -->\n", "", id="comment"),
        pytest.param("<![CDATA[raw]]>\n", "", id="cdata"),
        pytest.param("<?instruction?>\n", "", id="processing-instruction"),
        pytest.param("<!DOCTYPE x>\n", "", id="declaration"),
        pytest.param("<div>\nraw\n</div>\n", "", id="ordinary-html"),
        pytest.param("<span>\n", "", id="span-html"),
        pytest.param("text <span>inline</span>\n", "", id="inline-html"),
        pytest.param("> paragraph\n", "> ", id="quote-paragraph"),
        pytest.param("- paragraph\n", "  ", id="list-paragraph"),
        pytest.param("> # heading\n", "> ", id="quote-heading"),
        pytest.param("- # heading\n", "  ", id="list-heading"),
        pytest.param(">     code\n", "> ", id="quote-code"),
        pytest.param("-     code\n", "  ", id="list-code"),
        pytest.param("> [one]: /one\n", "> ", id="quote-definition"),
        pytest.param("- [one]: /one\n", "  ", id="list-definition"),
        pytest.param("> ```\n> code\n> ```\n", "> ", id="quote-fence"),
        pytest.param("- ```\n  code\n  ```\n", "  ", id="list-fence"),
        pytest.param("> <!-- hi -->\n", "> ", id="quote-comment"),
        pytest.param("- <!-- hi -->\n", "  ", id="list-comment"),
        pytest.param("> paragraph\n", "", id="quote-lazy-paragraph"),
        pytest.param("- paragraph\n", "", id="list-lazy-paragraph"),
    ],
)
def test_reference_definitions_start_only_at_native_block_boundaries(prefix: str, container: str, multiline: bool) -> None:
    """Only renderer-admitted definitions can turn an alt control into a real image."""
    definition = container + ("[course\n" + container + "image]: /x" if multiline else "[course image]: /x")
    source = "![?[{{goal}} A | B]][course image]\n\n" + prefix + definition
    image = "<img " in MarkdownIt().render(source)
    assert bool(list(find_document_image_labels(source))) is image
    controls = list(find_document_interaction_spans(source))
    assert [source[start:end] for start, end in controls] == ([] if image else ["?[{{goal}} A | B]"])
    replaced = replace_variables_in_text(source, {"goal": "old"}, add_quotes=False)
    assert replaced == (source.replace("{{goal}}", "old") if image else source)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("multiline", [False, True])
def test_paragraph_reference_lookalike_retains_the_actual_answer_binding(newline, multiline):
    definition = "[course\nimage]: /x" if multiline else "[course image]: /x"
    source = ("![?[{{goal}} A | B]][course image]\n\nparagraph\n" + definition).replace("\n", newline)
    assert "<img " not in MarkdownIt().render(source)
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ["?[{{goal}} A | B]"]
    assert flow.process(questions[0].index, user_input={"goal": ["A"]}).variables == {"goal": ["A"]}
