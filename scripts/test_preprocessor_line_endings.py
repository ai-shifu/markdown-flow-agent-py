"""Physical Markdown line boundaries preserve protected source exactly."""

import pytest

from markdown_flow.parser import CodeBlockPreprocessor


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("fence", ["```", "~~~"])
def test_fences_round_trip_and_do_not_mask_following_variable(ending, fence):
    source = ending.join([fence, "{{ unfinished", fence, "?[%{{ real }} A|B]"])
    processor = CodeBlockPreprocessor()
    processed = processor.extract_code_blocks(source)
    assert processed == "__MDFLOW_CODE_BLOCK_1__" + ending + "?[%{{ real }} A|B]"
    assert processor.restore_code_blocks(processed) == source
    assert processor.get_code_blocks() == {"__MDFLOW_CODE_BLOCK_1__": ending.join([fence, "{{ unfinished", fence])}


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
def test_comment_round_trip_and_removal_preserve_other_lines(ending):
    source = ending.join(["Before", "<!-- comment", "{{ unfinished", "-->", "After", ""])
    processor = CodeBlockPreprocessor()
    processed = processor.extract_code_blocks(source)
    assert processor.restore_code_blocks(processed) == source
    assert processor.remove_html_comment_placeholders(processed) == "Before" + ending + "After" + ending


@pytest.mark.parametrize("source", ["Before\r\n```\rcode\n```\rAfter", "<!-- comment\r\nbody\r-->\nAfter", "```\r\ncode\r", "<!--\r\ncomment\r", "{{\r\n question \r}}\nAfter"])
def test_mixed_endings_and_incomplete_blocks_preserve_exact_source(source):
    processor = CodeBlockPreprocessor()
    assert processor.restore_code_blocks(processor.extract_code_blocks(source)) == source


@pytest.mark.parametrize("separator", ["\x85", "\u2028", "\u2029"])
def test_unicode_separators_do_not_open_fences(separator):
    source = "Before" + separator + "~~~" + separator + "code" + separator + "~~~"
    processor = CodeBlockPreprocessor()
    assert processor.extract_code_blocks(source) == source
    assert not processor.code_blocks
