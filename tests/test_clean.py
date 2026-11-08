"""Unit tests for clean.py (Task 6 needs >= 3 tests; these are 4)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from worker.clean import clean  # noqa: E402


def _write_shard(tmp, name, rows):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return path


def test_rejects_invalid_json_and_wrong_keys(tmp_path):
    _write_shard(tmp_path, "shard-0.jsonl", [
        {"id": "C1", "text": "set an alarm for seven am", "teacher_raw": "not json"},
        {"id": "C2", "text": "set an alarm for seven am",
         "teacher_raw": '{"intent": "alarm_set", "date": null}'},
    ])
    out = clean(str(tmp_path), str(tmp_path / "v1"))
    assert out["a_invalid_json"] == 1 and out["b_wrong_keys"] == 1 and out["kept"] == 0


def test_rejects_bad_intent_and_slot_not_in_command(tmp_path):
    _write_shard(tmp_path, "shard-0.jsonl", [
        {"id": "C1", "text": "set an alarm for seven am",
         "teacher_raw": '{"intent": "fly_to_moon", "date": null, "time": null, "place": null}'},
        {"id": "C2", "text": "set an alarm for seven am",
         "teacher_raw": '{"intent": "alarm_set", "date": null, "time": "midnight", "place": null}'},
    ])
    out = clean(str(tmp_path), str(tmp_path / "v1"))
    assert out["c_bad_intent"] == 1 and out["d_bad_slot"] == 1 and out["kept"] == 0


def test_keeps_valid_row_and_deduplicates(tmp_path):
    raw = '{"intent": "alarm_set", "date": null, "time": "seven am", "place": null}'
    _write_shard(tmp_path, "shard-0.jsonl", [
        {"id": "C1", "text": "set an alarm for seven am", "teacher_raw": raw},
        {"id": "C1", "text": "set an alarm for seven am", "teacher_raw": raw},
    ])
    out = clean(str(tmp_path), str(tmp_path / "v1"))
    assert out["kept"] == 1 and out["e_duplicate"] == 1
    lines = open(tmp_path / "v1" / "train.jsonl", encoding="utf-8").read().strip().splitlines()
    assert json.loads(lines[0])["time"] == "seven am"


def test_counts_balance(tmp_path):
    raw = '{"intent": "alarm_set", "date": null, "time": "seven am", "place": null}'
    _write_shard(tmp_path, "shard-0.jsonl", [
        {"id": "C1", "text": "set an alarm for seven am", "teacher_raw": raw},
        {"id": "C2", "text": "set an alarm", "teacher_raw": "nope"},
    ])
    out = clean(str(tmp_path), str(tmp_path / "v1"))
    assert out["input"] == out["a_invalid_json"] + out["b_wrong_keys"] + out["c_bad_intent"] \
        + out["d_bad_slot"] + out["e_duplicate"] + out["kept"]
