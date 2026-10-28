"""Validated reference resources, rather than prefixes, close a paragraph."""

from unittest.mock import patch

import pytest
from markdown_it import MarkdownIt

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.constants import COMPILED_INLINE_HTML_REGEX
from markdown_flow.enums import BlockType
from markdown_flow.parser import document_blocks
from markdown_flow.parser.document_blocks import DocumentBlocks
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans


REFERENCE_BODIES = [
    "[one]: /one",
    "[one]: <one>",
    "[one]: <>",
    "[one]: /one (title)",
    '[one]: /one\n "title"',
    '[one]: /one "title\nmore"',
    "[one]:\n/one",
    "[one]:\n<one>",
    "[o\nne]: /one",
    "[o\\[ne]: /one",
    " [one]: /one",
    "[one]: /one trailing",
    '[one]: /one "unclosed',
    '[one]: /one "a\n\nb"',
    '[one]: /one\n "a\n\nb"',
    "[one]:",
    "[one] /one",
    "[o[ne]]: /one",
    "[o[ne]: /one",
    "\\[one]: /one",
    "[one]: <bad\nurl>",
    "[one]: /bad(unclosed",
    "[one]: /bad)end",
    "paragraph\n[one]: /one",
    "[one]: /one\nparagraph",
    "[one]: /one\n[two]: /two",
    "[one]: /one\n[two]: /two trailing",
    "[one]:\n\n/one",
    '[one]: /one "a\n2. item\nb"',
    '[one]: /one "a\n# heading\nb"',
    '[one]: /one "a\n===\nb"',
    '[one]: /one "a\n<!-- comment -->\nb"',
    "[one]: javascript:alert",
    "[one]: <javascript:alert>",
    "[one]: javascript\\:alert",
    "[one]: java&#x73;cript:alert",
    "[one]: &#106;avascript:alert",
    "[one]: vbscript:alert",
    "[one]: file:///one",
    "[one]: data:text/html,x",
    "[one]: data:image/svg+xml,x",
    "[one]: data:image/png;base64,x",
    "[one]: data:image/jpeg;base64,x",
    "[one]: https://example.com/one",
    "[one]: <relative path>",
]
CONTAINER_CONTEXTS = [("", ""), ("> ", "> "), ("- ", "  "), ("1. ", "   "), ("> - ", ">   "), ("- > ", "  > ")]


def _assert_contract(source: str, spelling: str) -> bool:
    control = "?[" + spelling + " A | B]"
    renderer = MarkdownIt()
    # Reference definitions remain definitions when the browser sanitizes URLs.
    with patch.object(renderer, "validateLink", return_value=True):
        image = "<img " in renderer.render(source)
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ([] if image else [control])
    replacement = source.replace("{{goal}}", "old") if image and spelling == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "old"}, add_quotes=False) == replacement
    return image


@pytest.mark.parametrize("body", REFERENCE_BODIES)
@pytest.mark.parametrize(("opening", "continuation"), CONTAINER_CONTEXTS)
@pytest.mark.parametrize("marker", ["2. ", "9) ", "2. [other]: /other\n3. "])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
def test_only_validated_reference_resources_admit_fresh_ordered_items(body: str, opening: str, continuation: str, marker: str, spelling: str) -> None:
    prefix = opening + body.replace("\n", "\n" + continuation)
    following = continuation + marker.replace("\n", "\n" + continuation)
    source = "![?[" + spelling + " A | B]][image]\n\n" + prefix + "\n" + following + "[image]: /x"
    _assert_contract(source, spelling)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(
    "body",
    [
        "> [one]:\n>\n> /one\n> 2. [image]: /x",
        '> [one]: /one "a\n>\n> b"\n> 2. [image]: /x',
        "> [o\n> # heading\n> ne]: /one\n> 2. [image]: /x",
        "> [o\n> - item\n> ne]: /one\n> 2. [image]: /x",
        "> [o\n> <!-- comment -->\n> ne]: /one\n> 2. [image]: /x",
        "[first]: /first\n2. > [o\n   > ne]: /one\n   > 3. [image]: /x",
        '[first]: /first\n2. > [one]: /one "a\n   > line\n   > b"\n   > 3. [image]: /x',
        "[first]: /first\n2. > [one]:\n   >\n   > /one\n   > 3. [image]: /x",
    ],
)
def test_reference_future_projection_uses_the_owning_container(body: str, spelling: str, newline: str) -> None:
    source = ("![?[" + spelling + " A | B]][image]\n\n" + body).replace("\n", newline)
    _assert_contract(source, spelling)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(("opening", "continuation"), CONTAINER_CONTEXTS)
@pytest.mark.parametrize("body", ["[one]: /one", "[one]: /one trailing", "[one]: javascript:alert", "[one]: /one (title)", '[one]: /one "a\n2. item\nb"'])
def test_reference_closures_keep_real_flow_image_and_answer_contracts(body: str, opening: str, continuation: str, spelling: str, newline: str) -> None:
    source = ("![?[" + spelling + " A | B]][image]\n\n" + opening + body.replace("\n", "\n" + continuation) + "\n" + continuation + "2. [image]: /x").replace("\n", newline)
    image = _assert_contract(source, spelling)
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ([] if image else ["?[" + spelling + " A | B]"])
    if questions:
        assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["A"]}).variables == {"goal": ["A"]}


@pytest.mark.parametrize("size", [100, 200, 400])
@pytest.mark.parametrize("unit", ["[one]: /one\n", "> [o\n> ne]: /one\n", '> [one]: /one "a\n> line\n> b"\n'])
def test_reference_closure_lookahead_has_bounded_work(monkeypatch: pytest.MonkeyPatch, size: int, unit: str) -> None:
    calls = 0
    original = document_blocks.DocumentBlocks.reference_projection

    def counted(self: DocumentBlocks, index: int, steps: tuple[int, ...]) -> tuple[int, str, bool]:
        nonlocal calls
        calls += 1
        return original(self, index, steps)

    monkeypatch.setattr(DocumentBlocks, "reference_projection", counted)
    blocks = DocumentBlocks(unit * size, COMPILED_INLINE_HTML_REGEX)
    assert calls <= 8 * len(blocks.lines)


@pytest.mark.parametrize(
    "destination",
    [
        "javascript:alert",
        "JAVASCRIPT:alert",
        r"javascript\:alert",
        "java&#x73;cript:alert",
        "&#106;avascript:alert",
        "&#x6a;avascript:alert",
        "jav&#Tab;ascript:alert",
        "&#Tab;javascript:alert",
        "\u00a0javascript:alert",
        "data:image/png;base64,x",
        "data:image/svg+xml,x",
        "data:text/html,x",
        "file:///one",
        "vbscript:alert",
        "https://example.com/one",
        "mailto:one@example.com",
        "/one",
        "relative path",
        "&#0000000000106;avascript:alert",
        "&notareal;javascript:alert",
        "&#11;javascript:alert",
        "&#xD800;javascript:alert",
        r"java\script:alert",
    ],
)
def test_destination_schemes_do_not_change_reference_block_closure(destination: str) -> None:
    """Sanitized URLs still close definitions before a fresh ordered-list item."""
    source = "![?[{{goal}} A | B]][image]\n\n[one]: <" + destination + ">\n2. [image]: /x"
    assert _assert_contract(source, "{{goal}}")
