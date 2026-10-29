"""Integration checks for text variable names with both interaction binding spellings."""

import json

import pytest

from markdown_flow import InteractionParser, MarkdownFlow
from markdown_flow.llm import LLMProvider, ProcessMode
from markdown_flow.variable_names import format_variable_reference


PREFIXES = ["", "%"]
KEYS = ["What is your goal?", "user name", "Which [path] | level//hint...?", "name}"]


@pytest.mark.parametrize("prefix", PREFIXES)
@pytest.mark.parametrize("key", KEYS)
def test_text_binding_keeps_memory_reads_separate_from_fresh_answers(prefix, key):
    reference = format_variable_reference(key)
    assert reference is not None
    binding = prefix + reference
    source = f"?[{binding} {reference} | {{{{reader}}}} | ...Explain]"
    memory: dict[str, str | list[str]] = {key: "Old answer", "reader": "Read value"}
    flow = MarkdownFlow(source)

    assert InteractionParser().parse(source)["variable"] == key
    assert flow.extract_variables() == sorted([key, "reader"])
    rendered = flow.process(0, variables=memory)
    assert rendered.content == f'?[{binding} """Old answer""" | """Read value""" | ...Explain]'
    assert InteractionParser().parse(rendered.content)["variable"] == key

    answer = flow.process(0, variables=memory, user_input={key: ["Fresh answer"]})
    assert answer.variables == {key: ["Fresh answer"]}
    assert memory == {key: "Old answer", "reader": "Read value"}


class TranslationProvider(LLMProvider):
    """Translate only the display fields sent through the real core request."""

    def __init__(self):
        self.payload = None

    def complete(self, messages, model=None, temperature=None):
        self.payload = json.loads(messages[-1]["content"])
        return json.dumps({"buttons": ["Aller", "Rester"], "question": "Votre réponse"})

    def stream(self, messages, model=None, temperature=None):
        response = self.complete(messages, model, temperature)
        yield response[: len(response) // 2]
        yield response[len(response) // 2 :]


@pytest.mark.parametrize("prefix", PREFIXES)
@pytest.mark.parametrize("mode", [ProcessMode.COMPLETE, ProcessMode.STREAM])
def test_translation_emits_standard_binding_without_rewriting_text_key_or_values(prefix, mode):
    key = "Go [path] | level//hint...}"
    reference = format_variable_reference(key)
    assert reference is not None
    source = f"?[{prefix}{reference} Go//go | Stay//stay | ...Your answer]"
    provider = TranslationProvider()
    flow = MarkdownFlow(source, llm_provider=provider)
    flow.set_prompt("output_language", "French")

    result = flow.process(0, mode=mode, variables={key: "Old answer"})
    if mode == ProcessMode.STREAM:
        results = list(result)
        assert len(results) == 1
        result = results[0]
    assert result.content == f"?[{reference} Aller//go | Rester//stay | ...Votre réponse]"
    parsed = InteractionParser().parse(result.content)
    assert parsed["variable"] == key
    assert [button["display"] for button in parsed["buttons"]] == ["Aller", "Rester"]
    assert [button["value"] for button in parsed["buttons"]] == ["go", "stay"]
    assert provider.payload == {"buttons": ["Go", "Stay"], "question": "Your answer"}
    assert flow.process(0, user_input={key: ["stay"]}).variables == {key: ["stay"]}


@pytest.mark.parametrize("prefix", PREFIXES)
@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_physical_line_endings_keep_padded_text_binding_and_multiline_body(prefix, newline):
    key = "Learning goal?"
    binding = prefix + "{{" + newline + key + newline + "}}"
    source = f"?[{binding} A |{newline}B]"
    flow = MarkdownFlow(source)
    assert InteractionParser().parse(source)["variable"] == key
    assert flow.process(0, variables={key: "Old answer"}).content == source
    result = flow.process(0, variables={key: "Old answer"}, user_input={key: ["B"]})
    assert result.variables == {key: ["B"]}
