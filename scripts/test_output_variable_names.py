"""Output operators cannot rewrite opaque variable names before substitution."""

import pytest

from markdown_flow import MarkdownFlow
from markdown_flow.constants import OUTPUT_INSTRUCTION_PREFIX, OUTPUT_INSTRUCTION_SUFFIX
from markdown_flow.parser import process_output_instructions


@pytest.mark.parametrize("key", ["a===b===c", "a!===b!===c", "===title===", "a{{===b===", "quotes'\\===b===}"])
def test_content_messages_substitute_names_that_contain_output_operators(key):
    source = "{{ " + key + " }}"
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == [key]
    user = flow.get_content_messages(0, {key: "VALUE"})[-1]["content"]
    assert user == '"""VALUE"""'
    assert "UNKNOWN" not in user
    assert process_output_instructions(source) == (source, False)


@pytest.mark.parametrize("outside", ["===OUT===", "!===OUT!===", "!===\nOUT\n!==="])
def test_real_output_operators_still_work_next_to_opaque_names(outside):
    source = "{{a===b===c}}\n" + outside
    transformed, preserved = process_output_instructions(source)
    assert preserved
    assert transformed == "{{a===b===c}}\n" + OUTPUT_INSTRUCTION_PREFIX + "OUT" + OUTPUT_INSTRUCTION_SUFFIX
    user = MarkdownFlow(source).get_content_messages(0, {"a===b===c": "VALUE"})[-1]["content"]
    assert '"""VALUE"""' in user
    assert OUTPUT_INSTRUCTION_PREFIX + "OUT" + OUTPUT_INSTRUCTION_SUFFIX in user
    assert "UNKNOWN" not in user


def test_variable_values_are_not_reinterpreted_as_output_instructions():
    user = MarkdownFlow("{{key}}").get_content_messages(0, {"key": "===VALUE==="})[-1]["content"]
    assert user == '"""===VALUE==="""'


@pytest.mark.parametrize("source", ["{{bad===name===\ninvalid}}", "%{{a===b===c}}", "{{bad===name===", "{{unfinished\n===not an operator==="])
def test_invalid_complete_markers_and_unclosed_tails_stay_atomic(source):
    assert process_output_instructions(source) == (source, False)


@pytest.mark.parametrize("source", ["{{a===b}} ===OUT===", "{{x{{===y===}} ===OUT==="])
def test_first_closing_pair_leaves_following_output_operators_active(source):
    transformed, preserved = process_output_instructions(source)
    assert preserved
    assert transformed == source.replace("===OUT===", OUTPUT_INSTRUCTION_PREFIX + "OUT" + OUTPUT_INSTRUCTION_SUFFIX)


def test_unclosed_literal_examples_do_not_hide_outside_output_operators():
    source = "`{{` ===OUT==="
    assert process_output_instructions(source) == ("`{{` " + OUTPUT_INSTRUCTION_PREFIX + "OUT" + OUTPUT_INSTRUCTION_SUFFIX, True)


def test_document_escaped_opener_keeps_existing_output_operator_behavior():
    source = r"\{{a===OUT===c}}"
    assert process_output_instructions(source) == (r"\{{a" + OUTPUT_INSTRUCTION_PREFIX + "OUT" + OUTPUT_INSTRUCTION_SUFFIX + "c}}", True)


def test_variable_marker_placeholders_cannot_collide_with_literal_source():
    source = "\x00mdf-output-name:0\x00 {{a===b===c}} ===OUT==="
    assert process_output_instructions(source) == ("\x00mdf-output-name:0\x00 {{a===b===c}} " + OUTPUT_INSTRUCTION_PREFIX + "OUT" + OUTPUT_INSTRUCTION_SUFFIX, True)


def test_inline_output_around_a_reference_does_not_modify_its_key():
    source = "==={{a===b===c}}==="
    user = MarkdownFlow(source).get_content_messages(0, {"a===b===c": "VALUE"})[-1]["content"]
    assert OUTPUT_INSTRUCTION_PREFIX + "VALUE" + OUTPUT_INSTRUCTION_SUFFIX in user
    assert "UNKNOWN" not in user
