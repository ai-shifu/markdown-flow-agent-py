"""Reference labels retain literal backslashes across projected physical lines."""

import pytest
from markdown_it import MarkdownIt

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import find_document_image_labels, find_document_interaction_spans


CONTAINERS = [("", ""), ("> ", "> "), ("- ", "  "), ("> - ", ">   "), ("- > ", "  > ")]


def _source(usage: str, definition: str | None, spelling: str, opening: str, continuation: str, before: bool, newline: str) -> str:
    image = opening + "![?[" + spelling + " A | B]][" + usage.replace("\n", "\n" + continuation) + "]"
    if definition is not None:
        reference = opening + "[" + definition.replace("\n", "\n" + continuation) + "]: /x"
        image = reference + "\n\n" + image if before else image + "\n\n" + reference
    return (image + "\n\nRead {{goal}}.\n\n?[{{visible}} C | D]").replace("\n", newline)


def _assert_contract(source: str, spelling: str, image: bool) -> None:
    control = "?[" + spelling + " A | B]"
    visible = "?[{{visible}} C | D]"
    assert ("<img " in MarkdownIt().render(source)) is image
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ([visible] if image else [control, visible])
    replacement = source.replace("Read {{goal}}.", "Read old.")
    if image and spelling == "{{goal}}":
        replacement = replacement.replace("{{goal}}", "old")
    assert replace_variables_in_text(source, {"goal": "old", "visible": "stale"}, add_quotes=False) == replacement
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == ([visible] if image else [control, visible])
    assert flow.process(questions[-1].index, variables={"goal": "old", "visible": "stale"}, user_input={"visible": ["D"]}).variables == {"visible": ["D"]}
    if not image:
        assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["B"]}).variables == {"goal": ["B"]}


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(("opening", "continuation"), CONTAINERS)
@pytest.mark.parametrize("before", [False, True])
@pytest.mark.parametrize("count", [1, 2, 3, 4])
@pytest.mark.parametrize("multiline", ["usage", "definition", "both"])
def test_backslashes_survive_label_line_endings_and_definition_projection(newline: str, spelling: str, opening: str, continuation: str, before: bool, count: int, multiline: str) -> None:
    prefix = "course" + "\\" * count
    usage = prefix + ("\n" if multiline in ("usage", "both") else " ") + "image"
    definition = prefix + ("\n" if multiline in ("definition", "both") else " ") + "image"
    _assert_contract(_source(usage, definition, spelling, opening, continuation, before, newline), spelling, True)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(("opening", "continuation"), CONTAINERS)
@pytest.mark.parametrize("before", [False, True])
@pytest.mark.parametrize("count", [1, 2, 3, 4])
@pytest.mark.parametrize("ending", ["[image", "]image", "ximage", "λimage", ""])
def test_only_ascii_punctuation_is_escaped_without_decoding_the_reference_identity(newline: str, spelling: str, opening: str, continuation: str, before: bool, count: int, ending: str) -> None:
    label = "course" + "\\" * count + ending
    if ending in ("[image", "]image"):
        image = count % 2 == 1
    elif not ending:
        image = count % 2 == 0
    else:
        image = True
    _assert_contract(_source(label, label, spelling, opening, continuation, before, newline), spelling, image)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(("opening", "continuation"), CONTAINERS)
@pytest.mark.parametrize("before", [False, True])
@pytest.mark.parametrize(
    ("usage", "definition"),
    [
        (r"course\:image", r"course\:image"),
        (r"course\!image", r"course\!image"),
        ("course\\\timage", "course\\ image"),
        ("course\\ \n image", "course\\ image"),
    ],
)
def test_reference_identity_preserves_backslashes_and_folds_only_whitespace(newline: str, spelling: str, opening: str, continuation: str, before: bool, usage: str, definition: str) -> None:
    _assert_contract(_source(usage, definition, spelling, opening, continuation, before, newline), spelling, True)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(("opening", "continuation"), CONTAINERS)
@pytest.mark.parametrize("before", [False, True])
@pytest.mark.parametrize(
    ("usage", "definition"),
    [
        ("course\\\nimage", None),
        ("course\\\nimage", "course image"),
        ("course\\\nimage", "course\\other"),
        ("course\\\n\nimage", "course\\ image"),
        ("course\\\n[image", "course\\ image"),
        (r"course\:image", "course:image"),
        (r"course\ximage", "courseximage"),
        ("course\\", "course\\"),
    ],
)
def test_undefined_or_malformed_escaped_labels_keep_real_answers(newline: str, spelling: str, opening: str, continuation: str, before: bool, usage: str, definition: str | None) -> None:
    _assert_contract(_source(usage, definition, spelling, opening, continuation, before, newline), spelling, False)
