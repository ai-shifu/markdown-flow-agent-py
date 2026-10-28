"""Captured learner controls and images share one rendered Markdown inventory."""

import json
import math
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any, SupportsIndex, cast, overload

import pytest

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser import document_context, rendered_reference_runs
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans
from markdown_flow.parser.rendered_reference_runs import Run, RunIndex, build_ownership


_CASES = json.loads(Path(__file__).with_name("rendered-reference-runs-observed-cases.json").read_text())["cases"]


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["id"])
def test_rendered_markdown_runs_match_captured_images_controls_and_answers(case: dict[str, Any]) -> None:
    source = case["source"]
    visible = bool(set(case["buttons"]) & {"A", "B"})
    marker = case["marker"]
    assert len(list(find_document_image_labels(source))) == case["images"]
    assert bool(list(find_document_interaction_spans(source))) is visible
    expected_replacement = source if visible or marker.startswith("%") else source.replace("{{goal}}", "old")
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == expected_replacement
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert bool(questions) is visible
    if questions:
        assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["B"]}).variables == {"goal": ["B"]}


_TARGETED = json.loads(Path(__file__).with_name("rendered-run-targeted-observed-cases.json").read_text())["cases"]


@pytest.mark.parametrize("case", _TARGETED, ids=lambda case: case["id"])
def test_streaming_tails_and_resource_metadata_match_the_real_renderer(case: dict[str, Any]) -> None:
    source = case["source"]
    observed = case["observed"]
    assert len(list(find_document_image_labels(source))) == len(observed["images"])
    expected_goal = bool(set(observed["buttons"]) & {"A", "B"})
    spans = list(find_document_interaction_spans(source))
    assert any("goal" in source[start:end] for start, end in spans) is expected_goal
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert any("goal" in block.content for block in questions) is expected_goal
    if case["kind"] == "content-slice-native-after":
        assert [block.content for block in questions] == ["?[{{visible}} C | D]"]
        prompt = flow.get_content_messages(0, {"goal": "old"})[-1]["content"]
        if case["marker"] == "{{goal}}":
            assert "old" in prompt
            assert "{{goal}}" not in prompt
        else:
            assert "%{{goal}}" in prompt
        assert flow.process(questions[0].index, variables={"visible": "old"}, user_input={"visible": ["D"]}).variables == {"visible": ["D"]}


@pytest.mark.parametrize("marker", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("wrapper", ["===Here is {control}===", "!===Here is {control}!===", "!===\nHere is {control}\n!==="])
def test_preserved_output_wrappers_still_split_actual_named_questions(marker: str, wrapper: str) -> None:
    control = "?[" + marker + " A | B]"
    flow = MarkdownFlow(wrapper.format(control=control))
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == [control]
    assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["A"]}).variables == {"goal": ["A"]}


def test_render_owner_index_is_lazy_and_shared_per_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    original = document_context.build_ownership

    def counted(*args: object, **kwargs: object) -> RunIndex:
        nonlocal calls
        calls += 1
        return cast(Callable[..., RunIndex], original)(*args, **kwargs)

    monkeypatch.setattr(document_context, "build_ownership", counted)
    assert len(list(find_document_interaction_spans("?[{{goal}} A | B]\n" * 100))) == 100
    assert calls == 0
    source = "![?[{{goal}} A | B]][image] " * 100 + "\n\n[image]: /x"
    assert len(list(find_document_image_labels(source))) == 100
    assert calls == 1


@pytest.mark.parametrize("size", [100, 1000, 10000])
def test_render_owner_queries_have_bounded_binary_search_work(size: int) -> None:
    work = 0

    class CountedStarts(tuple[int, ...]):
        __slots__ = ()

        @overload
        def __getitem__(self, key: SupportsIndex) -> int: ...

        @overload
        def __getitem__(self, key: slice) -> tuple[int, ...]: ...

        def __getitem__(self, key: SupportsIndex | slice) -> int | tuple[int, ...]:
            nonlocal work
            work += 1
            return super().__getitem__(key)

    owners = RunIndex(Run(index * 2, index * 2 + 2, "markdown") for index in range(size))
    owners.starts = CountedStarts(owners.starts)
    assert [owners.owner(index * 2) for index in range(size)] == list(range(size))
    assert 0 < work <= size * (math.ceil(math.log2(size)) + 1)


@pytest.mark.parametrize("size", [100, 1000, 4000])
def test_nested_html_render_ownership_reads_each_tag_a_bounded_number_of_times(monkeypatch: pytest.MonkeyPatch, size: int) -> None:
    calls = 0
    original = rendered_reference_runs.markup

    def counted(text: str, start: int) -> rendered_reference_runs.Markup:
        nonlocal calls
        calls += 1
        return original(text, start)

    monkeypatch.setattr(rendered_reference_runs, "markup", counted)
    source = "<details>" + "<div>" * size + "</div>" * size + "</details>"
    assert build_ownership(source).runs == (Run(0, len(source), "stable"),)
    assert calls <= 8 * (size + 1)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("marker", ["", "%"])
def test_code_placeholder_spelling_inside_a_binding_is_not_expanded(marker: str, newline: str) -> None:
    key = "__MDFLOW_CODE_BLOCK_1__"
    control = "?[" + marker + "{{" + key + "}} A | B]"
    source = (control + "\n\n```\ncode\n```").replace("\n", newline)
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == [control]
    assert flow.process(questions[0].index, variables={key: "old"}, user_input={key: ["A"]}).variables == {key: ["A"]}


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("marker", ["", "%"])
def test_authored_placeholder_text_inside_an_image_title_stays_literal(marker: str, newline: str) -> None:
    source = ("![?[" + marker + '{{goal}} A | B]](/x "__MDFLOW_CODE_BLOCK_1__")\n\n```\ncode\n```').replace("\n", newline)
    flow = MarkdownFlow(source)
    assert all(block.block_type != BlockType.INTERACTION for block in flow.get_all_blocks())
    assert flow.get_processed_document().count("__MDFLOW_CODE_BLOCK_1__") == 2


@pytest.mark.parametrize("marker", ["", "%"])
@pytest.mark.parametrize("preserved", [False, True])
def test_classified_image_content_keeps_references_after_a_following_question(marker: str, preserved: bool) -> None:
    image = "![?[" + marker + "{{answer}} A | B]][image]"
    content = "!===\n" + image + "\n!===" if preserved else image
    source = content + "\n\n?[{{real}} C | D]\n\n[image]: /image.png"
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ["?[{{real}} C | D]"]
    if preserved:
        output = flow.process(0, variables={"answer": "old"})
        assert isinstance(output, Generator)
        rendered = "".join(part.content for part in output)
    else:
        rendered = flow.get_content_messages(0, {"answer": "old"})[-1]["content"]
    if marker:
        assert "%{{answer}}" in rendered
    else:
        assert "old" in rendered
        assert "{{answer}}" not in rendered
    assert flow.process(questions[0].index, variables={"real": "stale"}, user_input={"real": ["C"]}).variables == {"real": ["C"]}


@pytest.mark.parametrize("marker", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_pending_doctype_scopes_only_image_alt_controls_and_keeps_generic_eof_fallback(marker: str, newline: str) -> None:
    source = ("Read {{read}}.\n\n<!DOCTYPE incomplete\n?[{{fallback}} C | D]\n![?[" + marker + " A | B]](/x)").replace("\n", newline)
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ["?[{{fallback}} C | D]"]
    rendered = replace_variables_in_text(source, {"read": "current", "goal": "old", "fallback": "stale"}, add_quotes=False)
    assert "Read current." in rendered
    assert "{{fallback}}" in rendered
    assert ("{{goal}}" in rendered) is marker.startswith("%")


@pytest.mark.parametrize("size", [100, 400, 1000])
@pytest.mark.parametrize("shape", ["unclosed", "ancestor-siblings", "nested-raw-ghost", "nested-complete", "distinct", "distinct-closed"])
def test_custom_button_html_scans_have_bounded_work(monkeypatch: pytest.MonkeyPatch, size: int, shape: str) -> None:
    calls = 0
    original = rendered_reference_runs.markup

    def counted(text: str, start: int) -> rendered_reference_runs.Markup:
        nonlocal calls
        calls += 1
        return original(text, start)

    monkeypatch.setattr(rendered_reference_runs, "markup", counted)
    if shape == "unclosed":
        body = "<custom-button-after-content>" * size
    elif shape == "ancestor-siblings":
        body = "<span><custom-button-after-content></span>" * size
    elif shape.startswith("distinct"):
        body = "".join("<tag" + str(index) + "><custom-button-after-content>" for index in range(size))
        if shape == "distinct-closed":
            body += "</custom-button-after-content>"
        body += "".join("</tag" + str(index) + ">" for index in range(size))
        body += '<script>"</custom-button-after-content>"</script>'
    else:
        body = "<span><custom-button-after-content>" * size + "</span>" * size
        body += '<script>"</custom-button-after-content>"</script>' if shape == "nested-raw-ghost" else "<custom-button-after-content>done</custom-button-after-content>"
    source = "<div>" + body + "</div>"
    assert build_ownership(source).runs
    assert calls <= 48 * (size + 1)


def test_foreign_closer_disables_the_root_only_html_balance_proof() -> None:
    opening = "<custom-button-after-content>"
    closing = "</custom-button-after-content>"
    source = "<div>" + opening + "<div>" + opening + "<span></div>" + opening + "</span>" + closing + "</div>"
    bounds: dict[int, int] = {}
    states: dict[tuple[int, str], int] = {}
    index = rendered_reference_runs._ClosingIndex(source)
    assert rendered_reference_runs.html_end(source, 0, siblings=True, element_ends=bounds, element_states=states, bound_index=index) == len(source)
    nested = source.index(opening, source.index(opening) + 1)
    assert rendered_reference_runs.html_end(source, nested, siblings=False, element_ends=bounds, element_states=states, bound_index=index) == source.index(closing) + len(closing)
