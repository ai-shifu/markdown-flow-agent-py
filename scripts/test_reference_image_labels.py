"""Full-reference image labels use projected paragraph text at original offsets."""

import pytest
from markdown_it import MarkdownIt

from markdown_flow import MarkdownFlow, replace_variables_in_text
from markdown_flow.enums import BlockType
from markdown_flow.parser.document_context import DocumentLiteralReader, find_document_image_labels, find_document_interaction_spans, read_image_reference_label


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(("opening", "continuation"), [("", ""), ("> ", "> "), ("> ", ""), ("> - ", "> "), ("- > ", "  > "), ("", "> ")])
@pytest.mark.parametrize(
    ("resource", "definition"),
    [
        ("[course image]", "course image"),
        ("[course\nimage]", "course image"),
        ("[course\n\nimage]", "course image"),
        ("[course\n# heading\nimage]", "course image"),
        ("[\ncourse image\n]", "course image"),
        ("[course\\\nimage]", "course image"),
        ("[course\nimage", "course image"),
        ("[course\nimage][other]", "course image"),
        ("[course\timage]", "course image"),
        ("[course \n image]", "course image"),
        ("[course\n> image]", "course image"),
        ("[course\n1. image]", "course 1. image"),
        ("[course\n2. image]", "course 2. image"),
        ("[course\n===\nimage]", "course === image"),
        (r"[course\[image\]]", r"course\[image\]"),
        ("[course {{ key[thing] }}]", "course {{ key[thing] }}"),
        ("[course\n<!-- x -->\nimage]", "course image"),
    ],
)
def test_full_reference_label_projection_matches_rendering(opening: str, continuation: str, resource: str, definition: str, spelling: str, newline: str) -> None:
    control = "?[" + spelling + " A | B]"
    source = (opening + "![" + control + "]" + resource.replace("\n", "\n" + continuation) + "\n\n[" + definition + "]: /x").replace("\n", newline)
    image = "<img " in MarkdownIt().render(source)
    assert bool(list(find_document_image_labels(source))) is image
    assert [source[start:end] for start, end in find_document_interaction_spans(source)] == ([] if image else [control])
    replacement = source.replace("{{goal}}", "old") if image and spelling == "{{goal}}" else source
    assert replace_variables_in_text(source, {"goal": "old", "key[thing]": "{{ key[thing] }}"}, add_quotes=False) == replacement


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("spelling", ["{{goal}}", "%{{goal}}"])
@pytest.mark.parametrize(("opening", "continuation"), [("", ""), ("> ", "> "), ("> ", ""), ("> - ", "> "), ("- > ", "  > "), ("", "> ")])
def test_projected_reference_images_keep_following_flow_answers(opening: str, continuation: str, spelling: str, newline: str) -> None:
    control = "?[" + spelling + " A | B]"
    image_source = (opening + "![" + control + "][course\n" + continuation + "image]\n\n[course image]: /x").replace("\n", newline)
    image = "<img " in MarkdownIt().render(image_source)
    source = image_source + newline * 2 + "Read {{goal}}." + newline * 2 + "?[{{visible}} C | D]"
    flow = MarkdownFlow(source)
    questions = [block for block in flow.get_all_blocks() if block.block_type == BlockType.INTERACTION]
    assert [block.content for block in questions] == (["?[{{visible}} C | D]"] if image else [control, "?[{{visible}} C | D]"])
    assert flow.process(questions[-1].index, variables={"visible": "old"}, user_input={"visible": ["D"]}).variables == {"visible": ["D"]}
    if not image:
        assert flow.process(questions[0].index, variables={"goal": "old"}, user_input={"goal": ["A"]}).variables == {"goal": ["A"]}


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("size", [999, 1000])
def test_label_length_excludes_projected_prefixes(newline: str, size: int) -> None:
    source = "> [" + "x" * 499 + newline + "> " + "y" * (size - 500) + "]"
    reader = DocumentLiteralReader(source)
    result = read_image_reference_label(source, 2, reader.blocks, reader.inline_limit(2))
    assert result == ("x" * 499 + "\n" + "y" * (size - 500) if size == 999 else None)


@pytest.mark.parametrize("size", [999, 1000])
def test_label_length_keeps_the_existing_escape_character_count(size: int) -> None:
    label = r"\*" * 499 + ("x" if size == 999 else "xx")
    source = "[" + label + "]"
    reader = DocumentLiteralReader(source)
    result = read_image_reference_label(source, 0, reader.blocks, reader.inline_limit(0))
    assert result == (label if size == 999 else None)
