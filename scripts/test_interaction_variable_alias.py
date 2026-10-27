"""Interaction bindings accept either variable spelling without changing references."""

import json

import pytest

from markdown_flow import InteractionParser, InteractionType, MarkdownFlow, ProcessMode
from markdown_flow.enums import BlockType
from markdown_flow.parser import extract_interaction_question, replace_variables_in_text


@pytest.mark.parametrize("prefix", ["%", ""])
@pytest.mark.parametrize(
    ("body", "kind", "values", "question"),
    [
        ("Yes//yes | No//no", InteractionType.BUTTONS_ONLY, ["yes", "no"], None),
        ("Yes//yes || No//no", InteractionType.BUTTONS_MULTI_SELECT, ["yes", "no"], None),
        ("...Explain", InteractionType.TEXT_ONLY, [], "Explain"),
        ("Yes//yes | No//no | ...Explain", InteractionType.BUTTONS_WITH_TEXT, ["yes", "no"], "Explain"),
        ("Yes//yes || No//no || ...Explain", InteractionType.BUTTONS_MULTI_WITH_TEXT, ["yes", "no"], "Explain"),
        ("Continue", InteractionType.BUTTONS_ONLY, ["Continue"], None),
    ],
)
def test_both_spellings_parse_all_named_interaction_shapes(prefix, body, kind, values, question):
    source = "?[ \t" + prefix + "{{ answer }} " + body + "]"
    parsed = InteractionParser().parse(source)
    assert parsed["variable"] == "answer"
    assert parsed["type"] == kind
    assert [button["value"] for button in parsed.get("buttons", [])] == values
    assert parsed.get("question") == question
    assert extract_interaction_question(source) == question


@pytest.mark.parametrize("prefix", ["%", ""])
@pytest.mark.parametrize("key", ["你的性别是？", "Which [path] | level//hint...?", "user  name", "a}", "outer{{inner", "path\\", "\ufeffkey\ufeff"])
def test_opaque_names_survive_render_and_named_answer_submission(prefix, key):
    source = "?[" + prefix + "{{ " + key + " }} First//one | Second//two]"
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == [key]
    assert flow.get_block(0).block_type == BlockType.INTERACTION
    for mode in (ProcessMode.COMPLETE, ProcessMode.STREAM):
        rendered = flow.process(0, mode=mode, variables={key: "old"})
        content = rendered.content if mode == ProcessMode.COMPLETE else "".join(result.content for result in rendered)
        assert content == source
        assert InteractionParser().parse(content)["variable"] == key
    result = flow.process(0, variables={key: "old"}, user_input={key: ["Second"]})
    assert result.variables == {key: ["two"]}


@pytest.mark.parametrize("prefix", ["%", ""])
@pytest.mark.parametrize("body", ["...Explain", "A | B | ...Explain", "A || B || ...Explain"])
def test_text_answers_store_the_bound_key_with_existing_memory(prefix, body):
    source = "?[" + prefix + "{{ answer }} " + body + "]"
    result = MarkdownFlow(source).process(0, variables={"answer": "old"}, user_input={"answer": ["new explanation"]})
    assert result.variables == {"answer": ["new explanation"]}


def test_replacement_preserves_only_real_leading_bindings():
    source = "Hello {{answer}}. ?[ {{ answer }} {{label}} | Other] Later {{answer}} %{{answer}}"
    assert replace_variables_in_text(source, {"answer": "old", "label": "Choose"}, add_quotes=False) == ("Hello old. ?[ {{ answer }} Choose | Other] Later old %{{answer}}")
    assert replace_variables_in_text("?[{{answer}} A | B]", add_quotes=False) == "?[{{answer}} A | B]"


@pytest.mark.parametrize("source", [r"\?[{{answer}} A | B]", "`?[{{answer}} A | B]`", "[example](url '?[{{answer}} A | B]')", '<span title="?[{{answer}} A | B]">'])
def test_literal_control_examples_do_not_claim_bare_bindings(source):
    assert replace_variables_in_text(source, {"answer": "old"}, add_quotes=False) == source.replace("{{answer}}", "old")


@pytest.mark.parametrize("prefix", ["%", ""])
@pytest.mark.parametrize("name", ["", "   ", "bad\nname", "bad\x00name"])
def test_invalid_leading_markers_do_not_create_named_interactions(prefix, name):
    source = "?[" + prefix + "{{" + name + "}} A | B]"
    assert InteractionParser().parse(source)["type"] is None


def test_nonleading_markers_remain_references_without_binding():
    source = "?[Continue {{answer}} | Cancel]"
    parsed = InteractionParser().parse(source)
    assert parsed["type"] == InteractionType.NON_ASSIGNMENT_BUTTON
    assert "variable" not in parsed
    assert replace_variables_in_text(source, {"answer": "old"}, add_quotes=False) == "?[Continue old | Cancel]"


@pytest.mark.parametrize(
    "source",
    [
        "![?[{{answer}} A | B]](url)",
        "![outer [nested] ?[{{answer}} A | B]](url)",
        "[![?[{{answer}} A | B]](image)](link)",
        "![?[{{answer}} A | B]][image]\n\n[image]: url",
        "![outer [nested] ?[{{answer}} A | B]][Image Label]\n\n[image label]: url",
    ],
)
def test_image_alt_text_keeps_bare_markers_as_references(source):
    assert replace_variables_in_text(source, {"answer": "old"}, add_quotes=False) == source.replace("{{answer}}", "old")
    flow = MarkdownFlow(source + "\n\n?[{{real}} Yes | No]")
    controls = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in controls] == ["?[{{real}} Yes | No]"]
    assert flow.process(controls[0].index, user_input={"real": ["Yes"]}).variables == {"real": ["Yes"]}


@pytest.mark.parametrize("source", ["![ ?[{{answer}} A | B]", "![?[{{answer}} A | B]][missing]", "![?[{{answer}} A | B]](unclosed"])
def test_unfinished_or_undefined_images_do_not_hide_a_real_binding(source):
    assert replace_variables_in_text(source, {"answer": "old"}, add_quotes=False) == source


def test_next_interaction_context_uses_the_binding_and_current_display_values():
    flow = MarkdownFlow("Introduction\n\n?[{{answer}} {{label}}//one | Second//two]")
    messages = flow.get_content_messages(0, {"answer": "old", "label": "First"})
    prompt = messages[-1]["content"]
    assert "First" in prompt
    assert "Second" in prompt
    assert "old" not in prompt


@pytest.mark.parametrize("prefix", ["%", ""])
def test_translation_preserves_either_binding_while_translating_controls(prefix):
    source = "?[" + prefix + "{{ Which [path] | level//hint...? }} Yes//yes | No//no | ...Explain]"
    flow = MarkdownFlow(source)
    translated = flow._reconstruct_with_translation(
        source,
        json.dumps({"buttons": ["Yes", "No"], "question": "Explain"}),
        json.dumps({"buttons": ["Oui", "Non"], "question": "Expliquer"}),
        InteractionParser().parse(source),
    )
    parsed = InteractionParser().parse(translated)
    assert parsed["variable"] == "Which [path] | level//hint...?"
    assert [button["value"] for button in parsed["buttons"]] == ["yes", "no"]
    assert [button["display"] for button in parsed["buttons"]] == ["Oui", "Non"]
    assert parsed["question"] == "Expliquer"
