"""Unit tests for the LLM JSON parsing helpers."""

import pytest

from retail_monitor.analyzers.json_utils import parse_json_response, sanitize_items_list


def test_parse_plain_json():
    out = parse_json_response('{"a": 1, "b": "x"}')
    assert out == {"a": 1, "b": "x"}


def test_parse_with_code_fence():
    text = "Some prose\n```json\n{\"alert_required\": true}\n```\nmore prose"
    out = parse_json_response(text)
    assert out == {"alert_required": True}


def test_parse_with_generic_fence():
    text = "```\n{\"k\": 2}\n```"
    out = parse_json_response(text)
    assert out == {"k": 2}


def test_parse_with_surrounding_text():
    text = "Here is your answer: {\"score\": 7.5}. Done."
    out = parse_json_response(text)
    assert out == {"score": 7.5}


def test_parse_tolerates_trailing_commas():
    text = '{"a": 1, "b": [1, 2, 3,],}'
    out = parse_json_response(text)
    assert out == {"a": 1, "b": [1, 2, 3]}


def test_parse_empty_raises():
    with pytest.raises(ValueError):
        parse_json_response("")


def test_parse_no_object_raises():
    with pytest.raises(ValueError):
        parse_json_response("totally not json")


def test_sanitize_strings_become_dicts():
    out = sanitize_items_list(["a bottle", "a box"])
    assert all(isinstance(x, dict) for x in out)
    assert out[0]["object"] == "a bottle"


def test_sanitize_skips_invalid():
    out = sanitize_items_list([{"object": "ok"}, 42, None, "string item"])
    assert len(out) == 2


def test_sanitize_non_list_returns_empty():
    assert sanitize_items_list(None) == []
    assert sanitize_items_list("not a list") == []
