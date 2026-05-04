"""L1 unit tests for the shared fence-stripping helper.

Closes the test-coverage gap noted in VIS-10: previously neither cast.py nor
attribute.py exercised the fence-stripping path — both their tests used bare
JSON, so the if-branch of `_FENCE_RE.search(...)` was dead in tests.
"""

from __future__ import annotations

from comicast.vision._parse import strip_fences


def test_strip_fences_passthrough_for_bare_json() -> None:
    assert strip_fences('{"a": 1}') == '{"a": 1}'


def test_strip_fences_extracts_json_tagged_fence() -> None:
    assert strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_strip_fences_extracts_untagged_fence() -> None:
    assert strip_fences('```\n{"a": 1}\n```') == '{"a": 1}'


def test_strip_fences_handles_prose_around_fence() -> None:
    raw = 'Sure! Here is the JSON:\n```json\n{"a": 1}\n```\nLet me know.'
    assert strip_fences(raw) == '{"a": 1}'


def test_strip_fences_returns_input_when_no_fence() -> None:
    assert strip_fences("plain text, no fences") == "plain text, no fences"
