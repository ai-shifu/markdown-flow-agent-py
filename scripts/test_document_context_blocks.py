"""Physical document contexts cannot hide later authored questions."""

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
