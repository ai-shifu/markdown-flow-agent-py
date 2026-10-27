"""Only native block-start reference definitions can classify an image label."""

import pytest
from markdown_it import MarkdownIt

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans


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
