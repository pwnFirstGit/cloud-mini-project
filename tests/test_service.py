"""Unit tests for the service's schema validation (Task 6).

Imports the real validator from service/validate.py — the same function
service/app.py uses — so the test exercises the production rule.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service"))
from validate import validate  # noqa: E402


def test_valid_frame_passes():
    assert validate('{"intent": "alarm_set", "date": null, "time": "seven am", "place": null}')


def test_extra_key_fails():
    assert validate('{"intent": "alarm_set", "date": null, "time": null, "place": null, "x": 1}') is None


def test_bad_intent_fails():
    assert validate('{"intent": "fly", "date": null, "time": null, "place": null}') is None


def test_broken_json_fails():
    assert validate("not json") is None
