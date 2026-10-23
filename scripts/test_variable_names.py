"""Offline conformance tests for text variable names and complete interaction boundaries."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from markdown_flow import InteractionParser, MarkdownFlow
from markdown_flow.enums import BlockType
from markdown_flow.llm import LLMProvider, ProcessMode
from markdown_flow.parser import CodeBlockPreprocessor, document_context, extract_interaction_question, extract_variables_from_text, generate_smart_validation_template, replace_variables_in_text
from markdown_flow.parser.variable import is_inside_preserve_tag
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


@pytest.mark.parametrize("tag", ["<原样输出>", "</原样输出>"])
@pytest.mark.parametrize("kind", ["reference", "assignment", "invalid", "invalid_assignment"])
@pytest.mark.parametrize("inside", [False, True])
def test_marker_contents_never_change_external_preserve_tag_state(tag, kind, inside):
    key = tag + ("\ninvalid" if kind.startswith("invalid") else "")
    marker = "{{" + key + "}}"
    if "assignment" in kind:
        marker = "%" + marker
    prefix = "<原样输出>" if inside else ""
    source = prefix + marker + " {{x}}"
    expected_first = marker if kind != "reference" else ("first" if inside else '"""first"""')
    expected_second = "second" if inside else '"""second"""'
    assert is_inside_preserve_tag(source, source.index("{{x}}")) == inside
    assert replace_variables_in_text(source, {key: "first", "x": "second"}) == prefix + expected_first + " " + expected_second


@pytest.mark.parametrize(
    ("source", "values", "expected"),
    [
        ("<原样输出>{{x}}</原样输出> {{y}}", {"x": "first", "y": "second"}, '<原样输出>first</原样输出> """second"""'),
        ("{{a}} {{x}}", {"a": "<原样输出>", "x": "second"}, '"""<原样输出>""" second'),
        ("<原样输出>{{a}} {{x}}", {"a": "</原样输出>", "x": "second"}, '<原样输出></原样输出> """second"""'),
        ("<原样输出>{{a}}样输出>{{x}}", {"a": "<原", "x": "second"}, "<原样输出><原样输出>second"),
    ],
)
def test_real_tags_and_tags_emitted_by_values_keep_historical_quote_behavior(source, values, expected):
    assert replace_variables_in_text(source, values) == expected


def test_many_opaque_markers_restore_exactly_alongside_code_comments_and_placeholder_collisions():
    count = 3000
    authored_placeholder = "\x00mdf-name:0\x00"
    chunks = [authored_placeholder]
    expected = [authored_placeholder]
    processor = CodeBlockPreprocessor()
    for i in range(count):
        marker = "{{ question " + str(i) + ' <!--literal--> "quoted"\\path }}'
        code = "```text\n{{ code " + str(i) + " }}\n```"
        comment = "<!--\n{{ comment " + str(i) + " }}\n-->"
        chunks.extend((marker, code, comment))
        expected.extend((marker, f"__MDFLOW_CODE_BLOCK_{2 * i + 1}__", f"__MDFLOW_HTML_COMMENT_{2 * i + 2}__"))
    assert processor.extract_code_blocks("\n".join(chunks)) == "\n".join(expected)
    assert len(processor.code_blocks) == len(processor.html_comments) == count
    for i in range(count):
        assert processor.code_blocks[f"__MDFLOW_CODE_BLOCK_{2 * i + 1}__"] == "```text\n{{ code " + str(i) + " }}\n```"
        assert processor.html_comments[f"__MDFLOW_HTML_COMMENT_{2 * i + 2}__"] == "<!--\n{{ comment " + str(i) + " }}\n-->"


@pytest.mark.parametrize(
    ("source", "values", "expected"),
    [
        ("{{x}} {{x}}", {"x": "<原样输出>"}, '"""<原样输出>""" """<原样输出>"""'),
        ("<原样输出>{{x}} {{x}}", {"x": "</原样输出>"}, "<原样输出></原样输出> </原样输出>"),
        ("{{x}} <原样输出>{{x}}</原样输出> {{x}}", {"x": "<原样输出>"}, '"""<原样输出>""" <原样输出><原样输出></原样输出> """<原样输出>"""'),
        ("{{x}} <原样输出>{{x}}</原样输出> {{x}}", {"x": "</原样输出>"}, '"""</原样输出>""" <原样输出></原样输出></原样输出> """</原样输出>"""'),
        ("{{x}} {{y}}", {"x": "<原样输出>", "y": "second"}, '"""<原样输出>""" second'),
        ("{{x}} {{y}}", {"y": "second", "x": "<原样输出>"}, '"""<原样输出>""" """second"""'),
        ("<原样输出>{{x}} {{y}}", {"x": "</原样输出>", "y": "second"}, '<原样输出></原样输出> """second"""'),
        ("<原样输出>{{x}} {{y}}", {"y": "second", "x": "</原样输出>"}, "<原样输出></原样输出> second"),
        ("<原样输出>{{a}}样输出>{{x}}", {"a": "</原", "x": "second"}, '<原样输出></原样输出>"""second"""'),
        ("<原样输出>{{a}}样输出>{{x}}", {"x": "second", "a": "</原"}, "<原样输出></原样输出>second"),
        ("{{x}} {{y}}", {"x": "{{y}}", "y": "second"}, '"""{{y}}""" """second"""'),
        ("{{x}} {{y}}", {"y": "second", "x": "{{y}}"}, '"""{{y}}""" """second"""'),
    ],
)
def test_replacement_preserves_per_key_snapshot_quoting_and_mapping_order(source, values, expected):
    assert replace_variables_in_text(source, values) == expected


@pytest.mark.parametrize(
    "example",
    ["`{{`", "``{{`inside``", r"\{{", r"\\`{{`", '<span title="{{">', "<span title='{{'>", "<span data-x={{>", "<?example {{ ?>", "<![CDATA[{{]]>"],
)
def test_literal_marker_examples_do_not_hide_external_fences_or_actual_interactions(example):
    source = example + "\n```js\ncode\n```\n?[A|B]"
    processor = CodeBlockPreprocessor()
    processed = processor.extract_code_blocks(source)
    assert len(processor.code_blocks) == 1
    assert "__MDFLOW_CODE_BLOCK_1__" in processed
    flow = MarkdownFlow(source)
    assert [block.block_type for block in flow.get_all_blocks()] == [BlockType.CONTENT, BlockType.INTERACTION]
    interaction = flow.get_block(1)
    assert [button["value"] for button in InteractionParser().parse(interaction.content)["buttons"]] == ["A", "B"]
    assert flow.process(1).content == "?[A|B]"
    result = flow.process(1, user_input={"input": ["A"]})
    assert result.variables == {}
    assert result.metadata["answer"] == ["A"]


@pytest.mark.parametrize("example", ["`{{`", "``{{`inside``", '<span title="{{">', "<span data-x={{>"])
@pytest.mark.parametrize("separator", [" then ", "\n"])
def test_document_extraction_and_replacement_never_cross_a_literal_markup_boundary(example, separator):
    source = "Show " + example + separator + "?[%{{ q }} A|B]"
    assert extract_variables_from_text(source) == ["q"]
    assert MarkdownFlow(source).extract_variables() == ["q"]
    reference = "Show " + example + separator + "{{ q }}"
    expected = "Show " + example + separator + '"""answer"""'
    assert replace_variables_in_text(reference, {"q": "answer"}) == expected
    messages = MarkdownFlow(reference).get_content_messages(0, {"q": "answer"})
    assert any(expected in message["content"] for message in messages)


def test_complete_variable_examples_inside_markup_keep_existing_collection_and_replacement():
    source = '`%{{ memory question? }}` <span title="{{ html key }}"> {{ q }}'
    assert MarkdownFlow(source).extract_variables() == ["html key", "memory question?", "q"]
    assert replace_variables_in_text(source, {"html key": "attribute", "q": "answer"}, add_quotes=False) == '`%{{ memory question? }}` <span title="attribute"> answer'
    assert replace_variables_in_text("`{{ q }}`", {"q": "answer"}) == '`"""answer"""`'


@pytest.mark.parametrize("source", ["`%{{ a<!-- literal -->b }}`", '<span title="%{{ a<!-- literal -->b }}">'])
def test_complete_variable_examples_keep_opaque_name_punctuation_during_preprocessing(source):
    flow = MarkdownFlow(source)
    assert flow.get_processed_document() == source
    assert flow.extract_variables() == ["a<!-- literal -->b"]


def test_document_escaped_openers_stay_literal_without_changing_raw_marker_apis():
    source = r"\{{ escaped }} {{ q }}"
    assert [marker.name for marker in find_variable_markers(source)] == ["escaped", "q"]
    assert extract_variables_from_text(source) == ["q"]
    assert replace_variables_in_text(source, {"escaped": "wrong", "q": "answer"}, add_quotes=False) == r"\{{ escaped }} answer"
    assert extract_variables_from_text(r"\\{{ q }}") == ["q"]
    assert replace_variables_in_text(r"\\{{ q }}", {"q": "answer"}, add_quotes=False) == r"\\answer"
    flow = MarkdownFlow(r"\{{ example ?[%{{ q }} A|B]")
    assert flow.extract_variables() == ["q"]
    assert flow.get_block(1).block_type == BlockType.INTERACTION


@pytest.mark.parametrize(("opening", "closing"), [("```js", "`````"), ("~~~text", "~~~~"), ("   ```", "  ````")])
def test_fenced_example_boundaries_use_real_fence_lengths_and_keep_legacy_collection_scope(opening, closing):
    example = opening + "\n{{\n" + closing
    source = example + "\n?[%{{ q }} A|B]"
    assert extract_variables_from_text(source) == ["q"]
    assert MarkdownFlow(source).extract_variables() == ["q"]
    assert replace_variables_in_text(example + "\n{{ q }}", {"q": "answer"}, add_quotes=False) == example + "\nanswer"
    complete = opening + "\n{{ example }}\n" + closing + "\n{{ q }}"
    assert extract_variables_from_text(complete) == ["example", "q"]
    assert MarkdownFlow(complete).extract_variables() == ["q"]
    assert replace_variables_in_text(complete, {"example": "literal", "q": "answer"}, add_quotes=False) == opening + "\nliteral\n" + closing + "\nanswer"


@pytest.mark.parametrize("prefix", ["{{outside", "`unclosed {{outside", r"\\{{outside", r"\`{{outside", '<span title="{{outside'])
def test_true_outside_unclosed_markers_still_own_the_remaining_document(prefix):
    source = prefix + "\n```js\ncode\n```\n?[A|B]"
    flow = MarkdownFlow(source)
    assert flow._preprocessor.code_blocks == {}
    assert flow.block_count == 1
    assert flow.get_block(0).block_type == BlockType.CONTENT
    assert flow.get_block(0).content == source


def test_true_raw_marker_names_own_markup_punctuation_before_document_lexing():
    key = 'question `{{` <span title="{{">?'
    source = "?[" + format_variable_assignment(key) + " A|B]"
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == [key]
    assert flow.block_count == 1
    assert InteractionParser().parse(flow.get_block(0).content)["variable"] == key
    assert flow.process(0, user_input={key: ["A"]}).variables == {key: ["A"]}


@pytest.mark.parametrize("case", CONTRACT["document_context_cases"], ids=lambda case: case["id"])
def test_shared_document_context_preserves_collection_replacement_and_real_answers(case):
    source = case["source"]
    flow = MarkdownFlow(source)
    assert extract_variables_from_text(source) == sorted(case["names"])
    assert flow.extract_variables() == sorted(case["names"])
    interactions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert len(interactions) == case["interaction_count"]
    for block in interactions:
        parsed = InteractionParser().parse(block.content)
        assert parsed.get("variable") == case["name"]
        assert [button["display"] for button in parsed["buttons"]] == case["buttons"]
        assert [button["value"] for button in parsed["buttons"]] == case["values"]
        key = case["name"] or "input"
        result = flow.process(block.index, user_input={key: [case["values"][0]]})
        if case["name"] is not None:
            assert result.variables == {key: [case["values"][0]]}
        else:
            assert result.metadata["answer"] == [case["values"][0]]
    replaced = replace_variables_in_text(source, dict.fromkeys(case["names"], "answer"), add_quotes=False)
    expected = "Show `answer` then ?[A|B]" if case["id"] == "complete-inline-code-reference" else source
    assert replaced == expected


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("slash_count", [1, 2, 3, 4])
def test_backslash_hard_breaks_do_not_hide_document_separators(newline, slash_count):
    slashes = "\\" * slash_count
    source = "A" + slashes + newline + "---" + newline + "B"
    blocks = MarkdownFlow(source).get_all_blocks()
    assert [block.block_type for block in blocks] == [BlockType.CONTENT, BlockType.CONTENT]
    assert [block.content for block in blocks] == ["A" + slashes, "B"]


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_multiple_hard_break_separators_keep_all_content_and_interaction_blocks(newline):
    source = newline.join(["A\\", "---", "B\\\\", "---", "?[A|B]", "---", "C\\\\\\", "---", "D"])
    flow = MarkdownFlow(source)
    assert [block.content for block in flow.get_all_blocks()] == ["A\\", "B\\\\", "?[A|B]", "C\\\\\\", "D"]
    assert [block.block_type for block in flow.get_all_blocks()] == [BlockType.CONTENT, BlockType.CONTENT, BlockType.INTERACTION, BlockType.CONTENT, BlockType.CONTENT]
    assert flow.process(2, user_input={"input": ["B"]}).metadata["answer"] == ["B"]


def test_document_escape_parity_still_distinguishes_literal_and_true_marker_openers():
    literal = MarkdownFlow(r"\{{ example" + "\n---\n?[%{{ q }} A|B]")
    assert literal.extract_variables() == ["q"]
    assert [block.block_type for block in literal.get_all_blocks()] == [BlockType.CONTENT, BlockType.INTERACTION]
    raw = MarkdownFlow(r"\\{{ outside" + "\n---\n?[A|B]")
    assert raw.block_count == 1
    assert raw.get_block(0).block_type == BlockType.CONTENT


@pytest.mark.parametrize("prefix", ["<!--", "<?", "<![CDATA[", "<!A"])
@pytest.mark.parametrize("earlier_closer", ["", "<!-- earlier --> <?done?> <![CDATA[done]]>\n"])
def test_impossible_html_tails_do_not_repeat_native_regex_work(prefix, earlier_closer):
    source = earlier_closer + prefix * 4096 + " {{ q }}"
    with patch.object(document_context, "COMPILED_INLINE_HTML_REGEX", wraps=document_context.COMPILED_INLINE_HTML_REGEX) as native:
        assert extract_variables_from_text(source) == ["q"]
    assert native.match.call_count <= 3


def test_html_tail_preflight_keeps_complete_native_literals_and_local_names():
    source = '<!-- {{ comment }} --> <?{{ instruction }}?> <![CDATA[{{ data }}]]> <span title="{{ attribute }}"> {{ q }}'
    assert extract_variables_from_text(source) == ["attribute", "comment", "data", "instruction", "q"]


@pytest.mark.parametrize(
    "prefix",
    [
        "    {{ unfinished\n\n",
        "\t{{ unfinished\n\n",
        " \t{{ unfinished\n\n",
        "Text\n\n    {{ unfinished\n\n",
        *[f"<{tag}>\n{{{{ unfinished\n</{tag.upper()}>\n" for tag in ("script", "style", "pre", "textarea")],
    ],
)
def test_block_literal_examples_cannot_hide_external_questions_or_references(prefix):
    question = "?[%{{ real }} A|B]"
    source = prefix + question
    assert extract_variables_from_text(source) == ["real"]
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == ["real"]
    interactions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert len(interactions) == 1
    parsed = InteractionParser().parse(interactions[0].content)
    assert parsed["variable"] == "real"
    assert [button["value"] for button in parsed["buttons"]] == ["A", "B"]
    assert flow.process(interactions[0].index, user_input={"real": ["B"]}).variables == {"real": ["B"]}
    reference = prefix + "{{ real }}"
    assert extract_variables_from_text(reference) == ["real"]
    assert replace_variables_in_text(reference, {"real": "VALUE"}, add_quotes=False) == prefix + "VALUE"


@pytest.mark.parametrize(
    "source", ["    {{ example }}\n\n{{ real }}", '<script title="{{">\n{{ example }}\n</script>\n{{ real }}', '<textarea title="{{ attribute }}">\n{{ example }}\n</textarea>\n{{ real }}']
)
def test_complete_block_examples_keep_local_collection_and_replacement(source):
    expected = ["attribute", "example", "real"] if "attribute" in source else ["example", "real"]
    assert extract_variables_from_text(source) == expected
    assert MarkdownFlow(source).extract_variables() == expected
    result = replace_variables_in_text(source, dict.fromkeys(expected, "VALUE"), add_quotes=False)
    for name in expected:
        assert "{{ " + name + " }}" not in result
    assert result.count("VALUE") == len(expected)


@pytest.mark.parametrize("width", [2, 3, 4])
def test_escaped_first_tick_still_allows_its_suffix_to_bound_a_local_example(width):
    prefix = "\\" + "`" * width + "{{" + "`" * (width - 1) + "\n"
    source = prefix + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    assert MarkdownFlow(source).extract_variables() == ["real"]
    assert MarkdownFlow(source).get_block(1).block_type == BlockType.INTERACTION
    assert replace_variables_in_text(prefix + "{{ real }}", {"real": "VALUE"}, add_quotes=False) == prefix + "VALUE"


def test_literal_block_ends_leave_separator_newlines_outside_and_preserve_fence_scope():
    for prefix in ["    {{ unfinished", "<script>\n{{ unfinished\n</script>"]:
        source = prefix + "\n\n---\n\n?[%{{ real }} A|B]"
        assert [block.block_type for block in MarkdownFlow(source).get_all_blocks()] == [BlockType.CONTENT, BlockType.INTERACTION]
    fenced = "```{{language}}\nx\n```"
    assert extract_variables_from_text(fenced) == ["language"]
    assert replace_variables_in_text(fenced, {"language": "python"}, add_quotes=False) == "```python\nx\n```"
    assert MarkdownFlow(fenced).extract_variables() == []


@pytest.mark.parametrize(
    "prefix", ["$x {{ y$", "$$x {{ y$$", r"\$$x {{ y$", '[x](url "{{")', "[x](url '{{')", "[x](url ({{))", '[x](u(n) "{{")', '[x](<url> "{{")', '![x](url "{{")', '[x](url\n "{{")']
)
def test_complete_math_and_link_resources_bound_unfinished_variable_examples(prefix):
    source = prefix + "\n\n?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == ["real"]
    interaction = flow.get_all_blocks()[-1]
    assert interaction.block_type == BlockType.INTERACTION
    assert flow.process(interaction.index, user_input={"real": ["A"]}).variables == {"real": ["A"]}
    assert replace_variables_in_text(prefix + "\n\n{{ real }}", {"real": "VALUE"}, add_quotes=False) == prefix + "\n\nVALUE"


@pytest.mark.parametrize("prefix", ["$x {{ example }}$", "$$x {{ example }}$$", '[x](url "{{ example }}")', '[x {{ label }}](url "{{ example }}")'])
def test_complete_variables_inside_math_and_link_resources_keep_historical_behavior(prefix):
    expected = ["example", "label"] if "label" in prefix else ["example"]
    assert extract_variables_from_text(prefix) == expected
    assert MarkdownFlow(prefix).extract_variables() == expected
    replaced = replace_variables_in_text(prefix, dict.fromkeys(expected, "VALUE"), add_quotes=False)
    assert replaced.count("VALUE") == len(expected)


@pytest.mark.parametrize("prefix", ["$x {{ unfinished", '[x](url "{{ unfinished', '[outer [inner](u)](u "{{")'])
def test_unconfirmed_math_or_inactive_outer_links_do_not_invent_literal_boundaries(prefix):
    source = prefix + "\n\n?[%{{ real }} A|B]"
    assert MarkdownFlow(source).extract_variables() == []
    assert all(block.block_type == BlockType.CONTENT for block in MarkdownFlow(source).get_all_blocks())


@pytest.mark.parametrize("delimiter", ["`", "$"])
def test_heading_line_boundaries_stop_inline_delimiters_without_changing_same_line_examples(delimiter):
    source = "# Heading " + delimiter + "{{\nq" + delimiter + " then ?[%{{ real }} A|B]"
    name = "q" + delimiter + " then ?[%{{ real"
    assert extract_variables_from_text(source) == [name]
    flow = MarkdownFlow(source)
    assert flow.extract_variables() == [name]
    assert all(block.block_type == BlockType.CONTENT for block in flow.get_all_blocks())
    same_line = "# Heading " + delimiter + "{{" + delimiter + "\n\n?[%{{ real }} A|B]"
    assert MarkdownFlow(same_line).extract_variables() == ["real"]
    assert MarkdownFlow(same_line).get_all_blocks()[-1].block_type == BlockType.INTERACTION
    next_heading = "Text " + delimiter + "{{\n# Heading q" + delimiter + " then ?[%{{ real }} A|B]"
    assert "real" not in MarkdownFlow(next_heading).extract_variables()


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_raw_html_closing_line_keeps_unfinished_examples_local_and_complete_examples_live(newline):
    prefix = newline.join(["<script>", "code", "</script> {{ unfinished", ""])
    source = prefix + "?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    assert MarkdownFlow(source).extract_variables() == ["real"]
    assert MarkdownFlow(source).get_all_blocks()[-1].block_type == BlockType.INTERACTION
    complete = newline.join(["<script>", "code", "</script> {{ example }}", "{{ real }}"])
    assert extract_variables_from_text(complete) == ["example", "real"]
    assert replace_variables_in_text(complete, {"example": "local", "real": "outside"}, add_quotes=False).endswith("local" + newline + "outside")


@pytest.mark.parametrize("width", [2, 3, 4])
def test_escaped_first_dollar_suffix_matches_native_math_boundaries(width):
    prefix = "\\" + "$" * width + "{{" + "$" * (width - 1)
    source = prefix + "\n\n?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    assert MarkdownFlow(source).get_all_blocks()[-1].block_type == BlockType.INTERACTION


@pytest.mark.parametrize(("depth", "names"), [(32, ["real"]), (33, [])])
def test_link_destination_nesting_matches_the_native_limit(depth, names):
    source = "[x](" + "(" * depth + "u" + ")" * depth + ' "{{ unfinished")\n\n?[%{{ real }} A|B]'
    assert extract_variables_from_text(source) == names


@pytest.mark.parametrize("prefix", ['[x](u<r "{{")', "[x](url (a({{))"])
def test_native_link_destination_and_title_characters_do_not_hide_external_questions(prefix):
    source = prefix + "\n\n?[%{{ real }} A|B]"
    assert extract_variables_from_text(source) == ["real"]
    assert MarkdownFlow(source).get_all_blocks()[-1].block_type == BlockType.INTERACTION


def test_interaction_bodies_keep_raw_markers_before_document_math():
    source = "?[%{{ q }} A ${{ y$ | B]\n\n?[%{{ real }} C|D]"
    assert extract_variables_from_text(source) == ["q"]
    blocks = MarkdownFlow(source).get_all_blocks()
    assert len(blocks) == 1
    assert blocks[0].block_type == BlockType.INTERACTION
    assert blocks[0].content == source
