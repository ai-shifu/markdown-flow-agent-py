"""Offline conformance tests for text variable names and complete interaction boundaries."""

import json
from pathlib import Path

import pytest

from markdown_flow import InteractionParser, MarkdownFlow
from markdown_flow.enums import BlockType
from markdown_flow.llm import LLMProvider, ProcessMode
from markdown_flow.parser import extract_interaction_question, extract_variables_from_text, generate_smart_validation_template, replace_variables_in_text
from markdown_flow.variable_names import find_variable_markers, format_variable_assignment, format_variable_reference, normalize_variable_name, read_variable_marker


CONTRACT = json.loads(Path(__file__).with_name("variable-name-contract.json").read_text())


@pytest.mark.parametrize("case", CONTRACT["normalization"])
def test_normalization_and_marker_round_trip(case):
    raw, name = case["raw"], case["name"]
    assert normalize_variable_name(raw) == name
    reference = format_variable_reference(raw)
    assert (reference is None) == (name is None)
    if reference is not None:
        marker = read_variable_marker(reference)
        assert marker is not None and marker.name == name and marker.end == len(reference)
        assert replace_variables_in_text(reference, {name: "answer"}, add_quotes=False) == "answer"


@pytest.mark.parametrize("case", CONTRACT["extraction"])
def test_first_close_and_non_recursive_extraction(case):
    source = case["source"]
    markers = list(find_variable_markers(source))
    assert list(dict.fromkeys(marker.name for marker in markers if marker.name is not None)) == case["names"]
    assert extract_variables_from_text(source) == sorted(case["names"])
    assert MarkdownFlow(source).extract_variables() == sorted(case["names"])


@pytest.mark.parametrize("case", CONTRACT["interactions"])
def test_interaction_document_boundaries_and_actual_answer(case):
    key, source = case["name"], case["source"]
    parser = InteractionParser()
    parsed = parser.parse(source)
    assert parsed["variable"] == key
    assert [button["display"] for button in parsed["buttons"]] == case["buttons"]
    assert [button["value"] for button in parsed["buttons"]] == case["values"]
    flow = MarkdownFlow("Before\n" + source + "\nAfter")
    assert [block.block_type for block in flow.get_all_blocks()] == [BlockType.CONTENT, BlockType.INTERACTION, BlockType.CONTENT]
    assert flow.extract_variables() == [key]
    result = flow.process(1, user_input={key: [case["values"][0]]})
    assert result.variables == {key: [case["values"][0]]}


def test_translation_changes_only_the_body_after_the_opaque_marker():
    key = "女|...Your answer|Yes//yes"
    source = "?[" + format_variable_assignment(key) + " Yes//yes | No//no | ...Your answer]"
    flow = MarkdownFlow(source)
    info = InteractionParser().parse(source)
    translated = flow._reconstruct_with_translation(
        source,
        json.dumps({"buttons": ["Yes", "No"], "question": "Your answer"}),
        json.dumps({"buttons": ["Oui", "Non"], "question": "Votre réponse"}),
        info,
    )
    parsed = InteractionParser().parse(translated)
    assert parsed["variable"] == key
    assert [button["display"] for button in parsed["buttons"]] == ["Oui", "Non"]
    assert parsed["question"] == "Votre réponse"
    assert extract_interaction_question(source) == "Your answer"


class TranslationProvider(LLMProvider):
    """Translate display text while recording the real request sent by core."""

    def __init__(self, corrupt=None):
        self.messages = []
        self.corrupt = corrupt

    def complete(self, messages, model=None, temperature=None):
        self.messages = messages
        payload = json.loads(messages[-1]["content"])

        def translate(text):
            text = text.replace("Your color", "Votre couleur").replace("Color", "Couleur").replace("Go", "Aller").replace("Which color?", "Quelle couleur ?")
            return self.corrupt(text) if self.corrupt else text

        if "buttons" in payload:
            payload["buttons"] = [translate(text) for text in payload["buttons"]]
        if "question" in payload:
            payload["question"] = translate(payload["question"])
        return json.dumps(payload, ensure_ascii=False)

    def stream(self, messages, model=None, temperature=None):
        response = self.complete(messages, model, temperature)
        yield response[: len(response) // 2]
        yield response[len(response) // 2 :]


def render_translation(flow, mode):
    result = flow.process(0, mode=mode)
    return list(result)[0] if mode == ProcessMode.STREAM else result


@pytest.mark.parametrize("mode", [ProcessMode.COMPLETE, ProcessMode.STREAM])
@pytest.mark.parametrize("key", ["Which color?", 'Which "color"?\\path', "Go]|...//<原样输出>key</原样输出>{"])
def test_core_translation_preserves_body_markers_and_translates_surrounding_text(mode, key):
    raw = "%" + format_variable_reference(key)
    source = "?[%{{ answer }} Color " + raw + "//blue | Go//go | ...Your color " + raw + "]"
    provider = TranslationProvider()
    flow = MarkdownFlow(source, llm_provider=provider)
    flow.set_prompt("output_language", "French")
    result = render_translation(flow, mode)
    parsed = InteractionParser().parse(result.content)
    assert parsed["variable"] == "answer"
    assert [button["display"] for button in parsed["buttons"]] == ["Couleur " + raw, "Aller"]
    assert [button["value"] for button in parsed["buttons"]] == ["blue", "go"]
    assert parsed["question"] == "Votre couleur " + raw
    payload = json.loads(provider.messages[-1]["content"])
    assert all(raw not in text and key not in text for text in [*payload["buttons"], payload["question"]])
    assert "opaque placeholders" in provider.messages[0]["content"]


@pytest.mark.parametrize("mode", [ProcessMode.COMPLETE, ProcessMode.STREAM])
@pytest.mark.parametrize("corruption", ["drop", "duplicate", "reorder", "rename"])
def test_core_translation_falls_back_per_field_when_marker_tokens_are_corrupted(mode, corruption):
    first, second = "%{{ Which color? }}", "%{{ Other color? }}"
    source = "?[%{{ answer }} Color " + first + " " + second + "//blue | Go//go | ...Your color " + first + " " + second + "]"

    def corrupt(text):
        first_token, second_token = "__MDFLOW_VARIABLE_1__", "__MDFLOW_VARIABLE_2__"
        if corruption == "drop":
            return text.replace(first_token, "")
        if corruption == "duplicate":
            return text.replace(first_token, first_token * 2)
        if corruption == "reorder":
            return text.replace(first_token + " " + second_token, second_token + " " + first_token)
        return text.replace(first_token, "__MDFLOW_VARIABLE_changed__")

    provider = TranslationProvider(corrupt)
    flow = MarkdownFlow(source, llm_provider=provider)
    flow.set_prompt("output_language", "French")
    parsed = InteractionParser().parse(render_translation(flow, mode).content)
    assert [button["display"] for button in parsed["buttons"]] == ["Color " + first + " " + second, "Aller"]
    assert parsed["question"] == "Your color " + first + " " + second


def test_translation_tokens_do_not_collide_and_reconstruction_does_not_match_inside_keys():
    raw = "%{{ Go// }}"
    source = "?[%{{ answer }} Keep __MDFLOW_VARIABLE_0__ " + raw + "//keep | Go]"
    provider = TranslationProvider()
    flow = MarkdownFlow(source, llm_provider=provider)
    flow.set_prompt("output_language", "French")
    parsed = InteractionParser().parse(flow.process(0).content)
    assert [button["display"] for button in parsed["buttons"]] == ["Keep __MDFLOW_VARIABLE_0__ " + raw, "Aller"]
    assert "___MDFLOW_VARIABLE_1__" in provider.messages[-1]["content"]


def test_translation_extraction_and_reconstruction_preserve_ordinary_references():
    raw = '{{ Which "color"?\\path }}'
    source = "?[%{{ answer }} Color " + raw + "//blue | ...Your color " + raw + "]"
    flow = MarkdownFlow(source)
    original_json, info = flow._extract_translatable_content(source)
    provider = TranslationProvider()
    translated_json = provider.complete([{"role": "user", "content": original_json}])
    parsed = InteractionParser().parse(flow._reconstruct_with_translation(source, original_json, translated_json, info))
    assert parsed["buttons"][0]["display"] == "Couleur " + raw
    assert parsed["question"] == "Votre couleur " + raw
    assert raw not in original_json


@pytest.mark.parametrize("source", ["?[%{{unterminated ?[Go]", "?[Color %{{unterminated ?[Go]", "?[Color {{unterminated ?[Go]"])
def test_unterminated_marker_source_is_not_submitted_for_interaction_translation(source):
    flow = MarkdownFlow(source)
    assert flow._extract_translatable_content(source)[0] == "{}"
    assert flow.get_block(0).block_type == BlockType.CONTENT
    assert flow.get_block(0).content == source


def test_validation_templates_encode_opaque_json_property_names():
    key = 'a"quoted\\path{key}'
    source = "?[" + format_variable_assignment(key) + " ...Your answer]"
    flow = MarkdownFlow(source)
    encoded = json.dumps(key, ensure_ascii=False)
    template = generate_smart_validation_template(key)
    assert encoded in template
    messages = flow._build_validation_messages(0, {key: ["answer"]}, key)
    assert encoded in messages[0]["content"]
    assert '"{target_variable}"' not in messages[0]["content"]


def test_replacement_is_opaque_and_never_reinterprets_a_nested_marker_or_value():
    assert replace_variables_in_text("{{bad\n{{inner}} {{valid}}", {"inner": "wrong", "valid": "right"}, add_quotes=False) == "{{bad\n{{inner}} right"
    assert replace_variables_in_text("{{ a }} {{ b }}", {"a": "{{ b }}", "b": "value"}, add_quotes=False) == "{{ b }} value"


def test_document_preprocessing_does_not_reinterpret_name_punctuation():
    key = "a<!-- comment -->b"
    source = "?[" + format_variable_assignment(key) + " A | B]"
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == [key]
    assert InteractionParser().parse(flow.get_block(0).content)["variable"] == key
    fenced = MarkdownFlow("```markdown\n" + source + "\n```")
    assert fenced.extract_variables() == []
    assert fenced._preprocessor.restore_code_blocks(fenced.get_processed_document()) == "```markdown\n" + source + "\n```"
    malformed = "{{a}<!-- -->}"
    assert MarkdownFlow(malformed).get_block(0).content == malformed
    assert MarkdownFlow(malformed).extract_variables() == []
    assert MarkdownFlow("```\n{{unterminated\n```\n?[Go]").get_block(1).block_type == BlockType.INTERACTION


@pytest.mark.parametrize("key", ["a\nb", "a\tb", "a\x00b", "a\u2028b", "a\u2029b"])
def test_invalid_control_keys_are_not_collected_or_assigned(key):
    source = "?[%{{ " + key + " }} A | B]"
    assert extract_variables_from_text(source) == []
    assert InteractionParser().parse(source)["type"] is None


@pytest.mark.parametrize("case", CONTRACT["boundary_cases"])
def test_shared_atomic_interaction_boundaries(case):
    source = case["source"]
    flow = MarkdownFlow(source)
    interactions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert len(interactions) == case["interaction_count"]
    if interactions:
        parsed = InteractionParser().parse(interactions[0].content)
        assert parsed.get("variable") == case["name"]
        assert [button["display"] for button in parsed["buttons"]] == case["buttons"]
        assert [button["value"] for button in parsed["buttons"]] == case["values"]
    else:
        assert len(flow.get_all_blocks()) == 1
        assert flow.get_block(0).content == source


def test_multiline_padding_is_trimmed_before_name_validation():
    reference = "{{\n name \n}}"
    assignment = "%" + reference
    source = "?[" + assignment + " A | B]"
    assert replace_variables_in_text(reference, {"name": "answer"}, add_quotes=False) == "answer"
    assert replace_variables_in_text(assignment, {"name": "answer"}, add_quotes=False) == assignment
    assert extract_variables_from_text(source) == ["name"]
    flow = MarkdownFlow(source)
    assert flow.block_count == 1
    assert flow.extract_variables() == ["name"]
    assert InteractionParser().parse(flow.get_block(0).content)["variable"] == "name"
