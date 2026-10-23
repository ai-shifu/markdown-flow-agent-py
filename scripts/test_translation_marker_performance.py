"""Translation marker work follows the fields present, not all global markers."""

import json

import pytest

from markdown_flow import MarkdownFlow
from markdown_flow.core import _restore_translation_markers, _translation_token_pattern


class CountedMarkers(dict[str, str]):
    """Count dictionary work without depending on wall-clock timing."""

    visits = 0
    lookups = 0

    def __iter__(self):
        for key in super().__iter__():
            self.visits += 1
            yield key

    def __contains__(self, key):
        self.lookups += 1
        return super().__contains__(key)

    def get(self, key, default=None):
        self.lookups += 1
        return super().get(key, default)


def test_many_translated_fields_do_not_rescan_the_global_marker_dictionary():
    count = 2000
    markers = CountedMarkers({f"__MDFLOW_VARIABLE_{index}__": "%{{key" + str(index) + "}}" for index in range(count)})
    token_pattern = _translation_token_pattern(markers)
    for index in range(count):
        token = f"__MDFLOW_VARIABLE_{index}__"
        assert _restore_translation_markers("Label " + token, "Translated " + token, markers, token_pattern) == "Translated %{{key" + str(index) + "}}"
    assert markers.visits <= 2 * count
    assert markers.lookups <= 4 * count


@pytest.mark.parametrize("corruption", ["drop", "duplicate", "reorder", "rename", None])
def test_single_pass_restoration_keeps_existing_token_validation(corruption):
    markers = {"__MDFLOW_VARIABLE_0__": "%{{first?}}", "__MDFLOW_VARIABLE_1__": r'{{second"\key}}'}
    first, second = markers
    original = "Original " + first + " " + second
    translated = "Changed " + first + " " + second + " __MDFLOW_VARIABLE_999__"
    if corruption == "drop":
        translated = translated.replace(first, "")
    elif corruption == "duplicate":
        translated = translated.replace(first, first * 2)
    elif corruption == "reorder":
        translated = translated.replace(first + " " + second, second + " " + first)
    elif corruption == "rename":
        translated = translated.replace(first, "__MDFLOW_VARIABLE_changed__")
    expected = original if corruption else translated
    for token, raw in markers.items():
        expected = expected.replace(token, raw)
    assert _restore_translation_markers(original, translated, markers) == expected


@pytest.mark.parametrize("literal", ["_" * 50000 + "MDFLOW_VARIABLE_", "".join(f"__MDFLOW_VARIABLE_N{index}_" for index in range(1024)), "__MDFLOW_VARIABLE_N" + "9" * 5000 + "_"])
def test_translation_collision_namespace_stays_short_and_preserves_author_text(literal):
    source = "?[%{{answer}} " + literal + " %{{key}} | Go]"
    flow = MarkdownFlow(source)
    original, info = flow._extract_translatable_content(source)
    assert literal in json.loads(original)["buttons"][0]
    assert all(len(token) < 50 for token in info["_translation_markers"])
    assert flow._reconstruct_with_translation(source, original, original, info) == source


def test_many_distinct_button_markers_share_the_interaction_lookup_index():
    count = 1000
    source = "?[%{{answer}} " + " | ".join("Label " + str(index) + " %{{key" + str(index) + "}}" for index in range(count)) + "]"
    original, info = MarkdownFlow(source)._extract_translatable_content(source)
    buttons = json.loads(original)["buttons"]
    assert len(buttons) == count
    assert len(info["_translation_markers"]) == count + 1
    assert all("%{{key" not in button for button in buttons)
