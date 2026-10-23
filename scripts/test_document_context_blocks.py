"""Physical document contexts cannot hide later authored questions."""

import json
from pathlib import Path

import pytest

from markdown_flow import InteractionParser, MarkdownFlow
from markdown_flow.enums import BlockType
from markdown_flow.parser import extract_variables_from_text, replace_variables_in_text
from markdown_flow.parser.document_context import find_document_variable_markers


PREFIXES = [
    "- ~~~\n  {{ unfinished\n  ~~~\n",
    "> ~~~\n> {{ unfinished\n> ~~~\n",
    "> - ~~~\n>   {{ unfinished\n>   ~~~\n",
    "1. ~~~\n   {{ unfinished\n   ~~~\n",
    "- > ~~~\n  > {{ unfinished\n  > ~~~\n",
    "~~~\n{{ unfinished\n~~~\n",
    "<div>\n{{ unfinished\n</div>\n\n",
    "<custom>\n{{ unfinished\n</custom>\n\n",
    "# Title\n    {{ unfinished\n\n",
    "~~~\ncode\n~~~\n    {{ unfinished\n\n",
    "Text\n---\n    {{ unfinished\n\n",
    "Text\n===\n    {{ unfinished\n\n",
    '[foo]: /url "{{ unfinished"\n\n',
    '[foo]: /url\n  "{{ unfinished"\n\n',
    "?[ unfinished\n\n`{{`\n\n",
]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("prefix", PREFIXES)
def test_physical_contexts_keep_the_actual_question_and_original_offsets(prefix, newline):
    prefix = prefix.replace("\n", newline)
    question = "?[%{{ real }} A|B]"
    source = prefix + question
    assert extract_variables_from_text(source) == ["real"]
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == ["real"]
    interactions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert len(interactions) == 1
    assert InteractionParser().parse(interactions[0].content)["variable"] == "real"
    assert flow.process(interactions[0].index, user_input={"real": ["B"]}).variables == {"real": ["B"]}
    assert replace_variables_in_text(prefix + "{{ real }}", {"real": "VALUE"}, add_quotes=False) == prefix + "VALUE"
    for marker in find_document_variable_markers(source):
        assert marker.raw_name == source[marker.start + 2 : marker.end - 2]


@pytest.mark.parametrize("source", ['[foo]: /url "{{ example }}"', '[foo]: /url\n  "{{ example }}"', "<div>\n{{ example }}\n</div>\n\n", "- ~~~\n  {{ example }}\n  ~~~\n"])
def test_complete_local_examples_keep_collection_and_replacement(source):
    assert extract_variables_from_text(source) == ["example"]
    assert MarkdownFlow(source).extract_variables() == ["example"]
    assert replace_variables_in_text(source, {"example": "VALUE"}, add_quotes=False) == source.replace("{{ example }}", "VALUE")


def test_incomplete_reference_title_does_not_change_true_raw_tail_ownership():
    source = '[foo]: /url "{{ unfinished\n\n?[%{{ real }} A|B]'
    assert extract_variables_from_text(source) == []
    assert all(block.block_type == BlockType.CONTENT for block in MarkdownFlow(source).get_all_blocks())


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize(("delimiter", "container"), [("`", "> "), ("`", "- "), ("$", "> "), ("$", "1. "), ("`", "---\n"), ("$", "---\n"), ("`", "<div>\n"), ("$", "<div>\n")])
def test_inline_delimiters_do_not_pair_across_confirmed_container_interrupts(newline, delimiter, container):
    container = container.replace("\n", newline)
    source = "Text " + delimiter + "{{ unfinished" + newline + container + delimiter + " end" + newline * 2 + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == []
    assert all(block.block_type == BlockType.CONTENT for block in MarkdownFlow(source).get_all_blocks())


@pytest.mark.parametrize("container", ["2. ", "x > "])
def test_noninterrupting_lines_keep_inline_literal_examples(container):
    source = "Text `{{ unfinished\n" + container + "` end\n\n?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]


@pytest.mark.parametrize("prefix", ["> `{{` then ", "- `{{` then ", "> `{{\n> x` then\n\n", "> `{{\nplain` then\n\n", "- `{{\n  x` then\n\n", "> ${{\n> x$ then\n\n", "> ${{\nplain$ then\n\n"])
def test_same_container_and_lazy_continuations_keep_complete_inline_literals(prefix):
    source = prefix + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("delimiter", ["`", "$"])
@pytest.mark.parametrize("underline", ["=", "===", "-", "--"])
def test_setext_heading_stops_inline_delimiter_pairing(newline, delimiter, underline):
    source = newline.join(["Text " + delimiter + "{{ unfinished", underline, delimiter + " end", "", "?[%{{ real }} A|B]"])
    assert extract_variables_from_text(source) == []
    assert all(block.block_type == BlockType.CONTENT for block in MarkdownFlow(source).get_all_blocks())
    assert replace_variables_in_text(source, {"real": "VALUE"}, add_quotes=False) == source


@pytest.mark.parametrize("delimiter", ["`", "$"])
@pytest.mark.parametrize("underline", ["=", "===", "-", "--"])
def test_complete_inline_examples_in_setext_headings_keep_their_names(delimiter, underline):
    prefix = "Text " + delimiter + "{{ example }}" + delimiter + "\n" + underline + "\n\n"
    source = prefix + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["example", "real"]
    assert MarkdownFlow(source).extract_variables() == ["example", "real"]
    assert replace_variables_in_text(source, {"example": "VALUE"}, add_quotes=False) == source.replace("{{ example }}", "VALUE")


@pytest.mark.parametrize("delimiter", ["`", "$"])
@pytest.mark.parametrize("line", ["== ordinary text", "=-", "    ==="])
def test_lines_that_are_not_setext_underlines_keep_the_inline_span(delimiter, line):
    source = "Text " + delimiter + "{{ unfinished\n" + line + "\n" + delimiter + " end\n\n?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]


HTML_CLOSING_LINE_CASES = [("<!--", "-->"), ("<?x", "?>"), ("<![CDATA[", "]]>"), ("<!DOCTYPE", ">")]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize(("opening", "closing"), HTML_CLOSING_LINE_CASES)
def test_complete_html_blocks_bound_unclosed_examples_on_the_closing_line(newline, opening, closing):
    prefix = newline.join([opening, "{{ unfinished", closing + " {{ still literal", ""])
    source = prefix + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == ["real"]
    controls = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert len(controls) == 1
    assert InteractionParser().parse(controls[0].content)["variable"] == "real"
    assert replace_variables_in_text(prefix + "{{ real }}", {"real": "VALUE"}, add_quotes=False) == prefix + "VALUE"


@pytest.mark.parametrize(("opening", "closing"), HTML_CLOSING_LINE_CASES)
def test_html_token_and_closing_line_keep_separate_complete_variable_examples(opening, closing):
    prefix = opening + "\n{{ unfinished\n" + closing + " {{ tail }}\n"
    source = prefix + "?[%{{ real }} A|B]"
    assert set(extract_variables_from_text(source)) == {"tail", "real"}
    assert replace_variables_in_text(source, {"tail": "VALUE"}, add_quotes=False) == source.replace("{{ tail }}", "VALUE")


@pytest.mark.parametrize(("opening", "closing"), HTML_CLOSING_LINE_CASES)
def test_inline_html_and_unclosed_tokens_keep_their_existing_boundaries(opening, closing):
    inline = "Text " + opening + "\n" + closing + " {{ still literal\n?[%{{ real }} A|B]"
    assert extract_variables_from_text(inline) == []
    unclosed = opening + "\n{{ example }}\n?[%{{ real }} A|B]"
    assert extract_variables_from_text(unclosed) == ["example", "real"]


CONTAINER_PREFIXES = [("> ", "> "), ("- ", "  "), ("1. ", "   "), ("> - ", ">   ")]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("delimiter", ["`", "$"])
@pytest.mark.parametrize(("first", "continued"), CONTAINER_PREFIXES)
def test_container_headings_interrupt_inline_pairing_at_original_offsets(newline, delimiter, first, continued):
    source = newline.join([first + "Text " + delimiter + "{{ unfinished", continued + "# Heading " + delimiter + " end", "", "?[%{{ real }} A|B]"])
    assert extract_variables_from_text(source) == []
    assert all(block.block_type == BlockType.CONTENT for block in MarkdownFlow(source).get_all_blocks())


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize(("first", "continued"), CONTAINER_PREFIXES)
@pytest.mark.parametrize("tag", ["div", "custom"])
@pytest.mark.parametrize("blank", [False, True])
def test_container_html_examples_end_at_blank_or_container_dedent(newline, first, continued, tag, blank):
    lines = [first + "<" + tag + ">", continued + "{{ unfinished", continued + "</" + tag + ">"]
    prefix = newline.join(lines) + newline * (2 if blank else 1)
    source = prefix + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    assert MarkdownFlow(source).extract_variables() == ["real"]
    assert sum(block.block_type == BlockType.INTERACTION for block in MarkdownFlow(source).get_all_blocks()) == 1
    assert replace_variables_in_text(prefix + "{{ real }}", {"real": "VALUE"}, add_quotes=False) == prefix + "VALUE"
    for marker in find_document_variable_markers(source):
        assert marker.raw_name == source[marker.start + 2 : marker.end - 2]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("tag", ["script", "style", "pre", "textarea"])
def test_closed_raw_html_allows_the_following_indented_example(newline, tag):
    prefix = newline.join(["<" + tag + ">", "</" + tag + ">", "    {{ unfinished", "", ""])
    source = prefix + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    assert MarkdownFlow(source).extract_variables() == ["real"]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("fence", ["~~~", "```"])
def test_stray_document_controls_end_before_a_confirmed_fence(newline, fence):
    source = newline.join(["?[ unfinished", fence, "{{ x", fence, "?[%{{ real }} A|B]"])
    assert extract_variables_from_text(source) == ["real"]
    assert MarkdownFlow(source).extract_variables() == ["real"]
    owned = newline.join(["?[%{{ unfinished", fence, "{{ x", fence, "?[%{{ real }} A|B]"])
    assert extract_variables_from_text(owned) == []
    assert all(InteractionParser().parse(block.content).get("variable") != "real" for block in MarkdownFlow(owned).get_all_blocks() if block.block_type == BlockType.INTERACTION)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize(("first", "continued"), CONTAINER_PREFIXES)
def test_container_reference_examples_keep_the_resource_local(newline, first, continued):
    source = first + '[foo]: /url "{{ unfinished"' + newline * 2 + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    assert MarkdownFlow(source).extract_variables() == ["real"]
    continuing = first + "Text" + newline + continued + '[foo]: /url "{{ unfinished"' + newline * 2 + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(continuing) == []


def test_inline_html_does_not_enable_a_following_indented_block():
    source = "Text <script></script>\n    {{ unfinished\n\n?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == []


@pytest.mark.parametrize(
    "prefix", ['> [foo]: /url\n>   "{{ unfinished"', '> [foo]:\n> /url "{{ unfinished"', '- [foo]: /url\n  "{{ unfinished"', '> [foo]: /url\n"{{ unfinished"', '> [foo]:\n/url "{{ unfinished"']
)
def test_multiline_container_reference_padding_keeps_original_resource_scope(prefix):
    source = prefix + "\n\n{{ real }}"
    assert extract_variables_from_text(source) == ["real"]


@pytest.mark.parametrize("prefix", ["> <div>\n> %{{ a|b[🙂] }}\n> </div>\n\n", '> [foo]: /url "%{{ a|b[🙂] }}"\n\n'])
def test_complete_container_examples_keep_exact_keys_and_source_offsets(prefix):
    source = prefix + "{{ other }}"
    assert set(extract_variables_from_text(source)) == {"a|b[🙂]", "other"}
    assert replace_variables_in_text(source, {"other": "VALUE"}, add_quotes=False) == prefix + "VALUE"
    for marker in find_document_variable_markers(source):
        assert marker.raw_name == source[marker.start + 2 : marker.end - 2]


@pytest.mark.parametrize("source", ["> <div>x\n", "- <div>x\n ", "> - <div>x\n>", "> - <div>x\n> "])
def test_incomplete_container_continuations_keep_html_pending(source):
    from markdown_flow.constants import COMPILED_INLINE_HTML_REGEX
    from markdown_flow.parser.document_blocks import DocumentBlocks

    block = DocumentBlocks(source, COMPILED_INLINE_HTML_REGEX).ordinary_html(0, final=False)
    assert block is not None
    assert not block.closed


def test_confirmed_container_dedent_closes_html_even_without_final_newline():
    from markdown_flow.constants import COMPILED_INLINE_HTML_REGEX
    from markdown_flow.parser.document_blocks import DocumentBlocks

    block = DocumentBlocks("> <div>x\nq", COMPILED_INLINE_HTML_REGEX).ordinary_html(0, final=False)
    assert block is not None
    assert block.closed


CONTAINER_COLUMN_CASES = [
    (">     {{ unfinished", True),
    ("> >     {{ unfinished", True),
    (">\t  {{ unfinished", True),
    ("> \t  {{ unfinished", True),
    ("-     {{ unfinished", True),
    ("- Intro\n\n      {{ unfinished", True),
    ("2. Intro\n\n       {{ unfinished", True),
    (">     {{ unfinished\n>\n>     still code", True),
    ("- Intro\n\n    ```\n  {{ unfinished\n    ```", True),
    ("2. Intro\n\n    ~~~\n   {{ unfinished\n    ~~~", True),
    ("- Intro\n\n\t  {{ unfinished", True),
    ("> \t~~~\n> {{ unfinished\n> \t~~~", True),
    ("> \t{{ unfinished", False),
    ("> Intro\n>     {{ unfinished", False),
    ("Paragraph\n    {{ unfinished", False),
    ("> - Intro\n>\n> \t  {{ unfinished", False),
]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize(("prefix", "real"), CONTAINER_COLUMN_CASES)
def test_container_columns_preserve_native_code_and_fence_boundaries(newline, prefix, real):
    prefix = prefix.replace("\n", newline) + newline * 2
    source = prefix + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == (["real"] if real else [])
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == (["real"] if real else [])
    assert sum(block.block_type == BlockType.INTERACTION for block in flow.get_all_blocks()) == int(real)
    assert replace_variables_in_text(prefix + "{{ real }}", {"real": "VALUE"}, add_quotes=False) == (prefix + "VALUE" if real else prefix + "{{ real }}")


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize(
    ("opening", "closing"),
    [("<script>", "</script>"), ("<style>", "</style>"), ("<pre>", "</pre>"), ("<textarea>", "</textarea>"), ("<!--", "-->"), ("<?x", "?>"), ("<![CDATA[", "]]>"), ("<!DOCTYPE", ">")],
)
@pytest.mark.parametrize(("first", "continued"), CONTAINER_PREFIXES + [("> \t", "> ")])
def test_every_existing_html_block_uses_container_columns(newline, opening, closing, first, continued):
    prefix = newline.join([first + opening, continued + "{{ unfinished", continued + closing, "", ""])
    source = prefix + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    assert MarkdownFlow(source).extract_variables() == ["real"]
    assert replace_variables_in_text(prefix + "{{ real }}", {"real": "VALUE"}, add_quotes=False) == prefix + "VALUE"


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("tag", ["script", "style", "pre", "textarea"])
@pytest.mark.parametrize(("first", "continued"), [("", ""), *CONTAINER_PREFIXES])
def test_raw_html_prefix_admits_blocks_without_a_complete_opening_tag(newline, tag, first, continued):
    prefix = newline.join([first + "<" + tag, continued.rstrip(), continued + "{{ unfinished", continued + "</" + tag + ">", "", ""])
    source = prefix + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    assert MarkdownFlow(source).extract_variables() == ["real"]
    assert replace_variables_in_text(prefix + "{{ real }}", {"real": "VALUE"}, add_quotes=False) == prefix + "VALUE"


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("opening", ["<!--", "<?x", "<![CDATA[", "<!DOCTYPE"])
@pytest.mark.parametrize(("first", "continued"), CONTAINER_PREFIXES)
def test_unterminated_container_html_ends_at_confirmed_parent_dedent(newline, opening, first, continued):
    prefix = newline.join([first + opening, continued + "{{ unfinished", continued + "{{ still unfinished", "", ""])
    source = prefix + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    assert MarkdownFlow(source).extract_variables() == ["real"]
    assert replace_variables_in_text(prefix + "{{ real }}", {"real": "VALUE"}, add_quotes=False) == prefix + "VALUE"


AUTOLINK_EXAMPLES = [
    "<foo:{{unfinished\x00>",
    "<foo:{{unfinished\ufffd>",
    "<foo:{{unfinished>",
    "<https://example.com/{{unfinished>",
    "<aa:{{unfinished>",
    "<" + "a" * 32 + ":{{unfinished>",
    "<foo:中文/{{unfinished>",
    "<{{unfinished@example.com>",
    "<{{unfinished@b>",
    "<{{unfinished@" + "a" * 63 + ".com>",
]
INVALID_AUTOLINK_EXAMPLES = [
    "<a:{{unfinished>",
    "<" + "a" * 33 + ":{{unfinished>",
    "<1foo:{{unfinished>",
    "<foo:{{unfinished space>",
    "<foo:{{unfinished\x7f>",
    "<foo:{{unfinished\x01>",
    "<foo:{{unfinished\n>",
    "<foo:{{unfinished",
    "<{{unfinished@-example.com>",
    "<{{unfinished@example-.com>",
    "<{{unfinished@" + "a" * 64 + ".com>",
    "<{{unfinished@@example.com>",
    "<{{unfinished@example..com>",
]
COMPLETE_AUTOLINK_KEYS = [
    ("<foo:%{{a|b[🙂]}}>", "a|b[🙂]"),
    (r"<foo:{{path\key}}>", r"path\key"),
    ("<{{question?}}@example.com>", "question?"),
    ("<foo:{{x<y}}>", "x<y"),
]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("example", AUTOLINK_EXAMPLES)
def test_complete_angle_autolinks_bound_unfinished_variable_examples(newline, example):
    prefix = example + newline * 2
    source = prefix + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == ["real"]
    assert sum(block.block_type == BlockType.INTERACTION for block in flow.get_all_blocks()) == 1
    assert replace_variables_in_text(prefix + "{{ real }}", {"real": "VALUE"}, add_quotes=False) == prefix + "VALUE"


@pytest.mark.parametrize("example", INVALID_AUTOLINK_EXAMPLES)
def test_invalid_or_unclosed_angle_links_do_not_claim_literal_scope(example):
    source = example + "\n\n?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == []
    assert MarkdownFlow(source).extract_variables() == []


@pytest.mark.parametrize(("example", "key"), COMPLETE_AUTOLINK_KEYS)
def test_complete_variable_declarations_inside_angle_links_keep_exact_keys(example, key):
    source = example + "\n\n?[%{{ real }} A|B]"
    assert set(extract_variables_from_text(source)) == {key, "real"}
    assert set(MarkdownFlow(source).extract_variables()) == {key, "real"}
    assert replace_variables_in_text(source, {key: "VALUE"}, add_quotes=False) == (source if "%{{" in example else source.replace("{{" + key + "}}", "VALUE"))
    for marker in find_document_variable_markers(source):
        assert marker.raw_name == source[marker.start + 2 : marker.end - 2]


def test_true_markers_remain_opaque_before_angle_link_syntax():
    source = "{{ key<foo:?[Go]> }}\n\n?[%{{ real }} A|B]"
    assert set(extract_variables_from_text(source)) == {"key<foo:?[Go]>", "real"}
    assert sum(block.block_type == BlockType.INTERACTION for block in MarkdownFlow(source).get_all_blocks()) == 1


AUTOLINK_CORPUS = json.loads(Path(__file__).with_name("autolink-cases.json").read_text())


@pytest.mark.parametrize("case", AUTOLINK_CORPUS, ids=lambda case: case["id"])
def test_shared_native_angle_autolink_corpus(case):
    source = case["source"]
    assert extract_variables_from_text(source) == case["names"]
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == case["names"]
    assert bool([block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]) == ("real" in case["names"])


def test_angle_link_continuation_witness_preserves_native_acceptance():
    from markdown_flow.parser.document_blocks import compact_angle_autolink_prefix, read_angle_autolink

    prefixes = ["<", "<f", "<foo", "<script", "<SCRIPT", "<" + "a" * 32, "<" + "a" * 33, "<foo:", "<foo:{{", "<{{", "<{{unfinished@a", "<a@b.", "<a@" + "x" * 63, "<a@" + "x" * 61 + "-"]
    suffixes = [">", ":u>", ":{{unfinished>", "@b>", "b>", "->", ".b>", "@b:>", " {{", " ", "\n", "<", "$", "-", ":"]
    for prefix in prefixes:
        witness = compact_angle_autolink_prefix(prefix, 0)
        assert witness is not None
        assert len(witness) <= 70
        for suffix in suffixes:
            assert (read_angle_autolink(prefix + suffix, 0) is not None) == (read_angle_autolink(witness + suffix, 0) is not None), (prefix, suffix, witness)
    for prefix in ["<foo:" + "u" * 50000, "<" + "a" * 50000, "<" + "x" * 50000 + "@" + "d." * 10000 + "tail"]:
        witness = compact_angle_autolink_prefix(prefix, 0)
        assert witness is not None and len(witness) <= 70
