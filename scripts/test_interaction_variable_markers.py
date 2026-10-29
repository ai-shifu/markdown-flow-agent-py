"""Offline checks for standard interaction bindings and legacy percent compatibility."""

import json

import pytest

from markdown_flow import InteractionParser, MarkdownFlow
from markdown_flow.enums import BlockType
from markdown_flow.llm import LLMProvider, ProcessMode
from markdown_flow.parser import replace_variables_in_text


MARKERS = ["{{choice}}", "%{{choice}}"]
MODES = [ProcessMode.COMPLETE, ProcessMode.STREAM]
SHAPES = [
    ("A//a | B//b", "buttons_only", ["b"]),
    ("A//a || B//b", "buttons_multi_select", ["a", "b"]),
    ("...Explain", "text_only", ["Fresh answer"]),
    ("A//a | ...Explain", "buttons_with_text", ["a", "Fresh answer"]),
    ("A//a || ...Explain", "buttons_multi_with_text", ["a", "Fresh answer"]),
]


def process(flow, mode, **kwargs):
    result = flow.process(0, mode=mode, **kwargs)
    if mode == ProcessMode.STREAM:
        results = list(result)
        assert len(results) == 1
        return results[0]
    return result


class RecordingProvider(LLMProvider):
    """Return deterministic responses while retaining the actual core request."""

    def __init__(self, response):
        self.response = json.dumps(response)
        self.messages = []

    def complete(self, messages, model=None, temperature=None):
        self.messages = messages
        return self.response

    def stream(self, messages, model=None, temperature=None):
        response = self.complete(messages, model, temperature)
        yield response[: len(response) // 2]
        yield response[len(response) // 2 :]


@pytest.mark.parametrize("marker", MARKERS)
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("body,kind,answer", SHAPES)
def test_parse_render_and_fresh_answers(marker, mode, body, kind, answer):
    source = f"?[{marker} {body}]"
    parsed = InteractionParser().parse(source)
    assert parsed["variable"] == "choice"
    assert parsed["type"].value == kind
    flow = MarkdownFlow(source)
    assert flow.get_block(0).block_type == BlockType.INTERACTION
    assert flow.extract_variables() == ["choice"]
    assert process(flow, mode).content == source
    memory = {"choice": "Old answer"}
    assert process(flow, mode, variables=memory).content == source
    result = process(flow, mode, variables=memory, user_input={"choice": answer})
    assert result.variables == {"choice": answer}
    assert memory == {"choice": "Old answer"}


@pytest.mark.parametrize("marker", MARKERS)
@pytest.mark.parametrize("mode", MODES)
def test_binding_is_preserved_while_same_key_and_other_body_references_are_read(marker, mode):
    source = f"?[{marker} {{{{choice}}}} | {{{{name}}}}]"
    result = process(MarkdownFlow(source), mode, variables={"choice": "Old answer", "name": "Alice"})
    assert result.content == f'?[{marker} """Old answer""" | """Alice"""]'


@pytest.mark.parametrize("marker", MARKERS)
@pytest.mark.parametrize("mode", MODES)
def test_padded_binding_and_leading_whitespace_keep_the_trimmed_key(marker, mode):
    padded = marker.replace("choice", " choice ")
    source = f"?[ \t{padded} A//a | B//b]"
    flow = MarkdownFlow(source)
    assert process(flow, mode, variables={"choice": "Old answer"}).content == source
    result = process(flow, mode, variables={"choice": "Old answer"}, user_input={"choice": ["b"]})
    assert result.variables == {"choice": ["b"]}


@pytest.mark.parametrize(
    "source,expected",
    [
        ("Hello {{choice}}", 'Hello """Alice"""'),
        ("?[A | {{choice}}]", '?[A | """Alice"""]'),
        (r"\?[{{choice}} A | B]", r'\?["""Alice""" A | B]'),
        ("?[{{choice}} A | B", '?["""Alice""" A | B'),
        ("?[{{choice}} A](url)", '?["""Alice""" A](url)'),
        ("%{{choice}} / {{choice}}", '%{{choice}} / """Alice"""'),
    ],
)
def test_non_bindings_keep_existing_reference_replacement(source, expected):
    assert replace_variables_in_text(source, {"choice": "Alice"}) == expected


@pytest.mark.parametrize("marker", MARKERS)
def test_earlier_reference_growth_does_not_expose_a_later_binding_to_replacement(marker):
    source = f"{{{{intro}}}} ?[{marker} A | {{{{label}}}}]"
    memory = {"intro": "Longer introduction", "choice": "Old answer", "label": "New label"}
    assert replace_variables_in_text(source, memory) == f'"""Longer introduction""" ?[{marker} A | """New label"""]'


@pytest.mark.parametrize("marker", MARKERS)
@pytest.mark.parametrize("answered", [False, True])
def test_history_uses_saved_binding_answers_and_skips_unanswered_bindings(marker, answered):
    flow = MarkdownFlow("Follow up")
    context = [{"role": "assistant", "content": f"?[{marker} A | B]"}]
    memory: dict[str, str | list[str]] = {"choice": ["Saved answer"]} if answered else {}
    messages = flow.get_content_messages(0, memory, context)
    expected = [{"role": "user", "content": "Saved answer"}, {"role": "assistant", "content": "ok"}] if answered else []
    assert messages[1:-1] == expected


@pytest.mark.parametrize("marker", MARKERS)
def test_next_interaction_hint_uses_options_and_reads_without_leaking_memory(marker):
    flow = MarkdownFlow(f"Introduction\n?[{marker} A//a | B//b | ...Hello {{{{name}}}}]")
    messages = flow.get_content_messages(0, {"choice": "Old answer", "name": "Alice"})
    request = "\n".join(message["content"] for message in messages)
    assert "# Next Interaction Note" in request
    assert '["A", "B"]' in request
    assert "Alice" in request
    assert "Old answer" not in request
    assert marker not in request


@pytest.mark.parametrize("marker", ["{{Go}}", "%{{Go}}"])
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("choices,values", [("Go | Stay", ["Go", "Stay"]), ("Go//go | Stay//stay", ["go", "stay"])])
def test_translation_keeps_the_key_and_values_and_emits_standard_binding(marker, mode, choices, values):
    provider = RecordingProvider({"buttons": ["Aller", "Rester"], "question": "Expliquez"})
    flow = MarkdownFlow(f"?[{marker} {choices} | ...Explain]", llm_provider=provider)
    flow.set_prompt("output_language", "French")
    result = process(flow, mode, variables={"Go": "Old answer"})
    assert result.content == f"?[{{{{Go}}}} Aller//{values[0]} | Rester//{values[1]} | ...Expliquez]"
    parsed = InteractionParser().parse(result.content)
    assert parsed["variable"] == "Go"
    assert [button["value"] for button in parsed["buttons"]] == values
    assert json.loads(provider.messages[-1]["content"]) == {"buttons": ["Go", "Stay"], "question": "Explain"}
    answer = process(flow, mode, variables={"Go": "Old answer"}, user_input={"Go": [values[0]]})
    assert answer.variables == {"Go": [values[0]]}


@pytest.mark.parametrize("marker", MARKERS)
@pytest.mark.parametrize("mode", MODES)
def test_text_validation_uses_the_binding_key_and_actual_fresh_input(marker, mode):
    provider = RecordingProvider({"result": "ok", "parse_vars": {"choice": "Fresh answer"}})
    flow = MarkdownFlow(f"?[{marker}...Explain]", llm_provider=provider)
    flow.set_text_validation_enabled(True)
    result = process(flow, mode, variables={"choice": "Old answer"}, user_input={"choice": ["Fresh answer"]})
    assert result.variables == {"choice": ["Fresh answer"]}
    assert provider.messages[-1] == {"role": "user", "content": "Fresh answer"}
    assert '"choice"' in provider.messages[0]["content"]
    assert "Explain" in provider.messages[0]["content"]


@pytest.mark.parametrize("mode", MODES)
def test_non_assignment_answers_and_history_keep_existing_behavior(mode):
    source = "?[Continue|Cancel]"
    flow = MarkdownFlow(source)
    assert process(flow, mode).content == source
    result = process(flow, mode, user_input={"input": ["Continue"]})
    assert result.variables == {}
    assert result.metadata["answer"] == ["Continue"]
    context = [{"role": "assistant", "content": source, "user_answer": "Continue"}]
    messages = MarkdownFlow("Follow up").get_content_messages(0, {}, context)
    assert messages[1:-1] == [{"role": "user", "content": "Continue"}, {"role": "assistant", "content": "ok"}]
