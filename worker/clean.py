"""Clean teacher labels into the v1 training set (Task 1).

Rejection rules, in order — a shard line is dropped at the first rule it
fails (counts are reported per rule so the report's table balances):
  (a) teacher_raw is not valid JSON
  (b) JSON is not an object with exactly the keys intent, date, time, place
  (c) intent is not one of the 8 intents in student_kit/data/schema.json
  (d) a slot value is neither null nor a substring of the command text
      (compared after lower-casing and stripping, as score.py does)
  (e) duplicate (id, text) — keep the smallest id (shards are processed in
      id order, so the first occurrence wins)

Usage: python3 worker/clean.py datasets/teacher datasets/v1
Writes datasets/v1/train.jsonl ({"id", "text", "intent", "date", "time",
"place"}, id order) + train.sha256. Re-running must reproduce the checksum.
"""
import hashlib
import json
import os
import sys

KEYS = {"intent", "date", "time", "place"}


def load_intents(schema_path: str) -> set:
    with open(schema_path, encoding="utf-8") as f:
        return set(json.load(f)["intents"])


def _default_schema_path() -> str:
    # Resolve against the repo root (parent of worker/), not the cwd, so
    # `make clean` and pytest work from anywhere. Fall back to the
    # cwd-relative path if the kit has not been copied into the repo yet.
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cand = os.path.join(repo, "student_kit", "data", "schema.json")
    return cand if os.path.exists(cand) else "student_kit/data/schema.json"


def clean(teacher_dir: str, out_dir: str, schema_path: str = None) -> dict:
    if schema_path is None:
        schema_path = _default_schema_path()
    intents = load_intents(schema_path)
    counts = {"input": 0, "a_invalid_json": 0, "b_wrong_keys": 0, "c_bad_intent": 0,
              "d_bad_slot": 0, "e_duplicate": 0, "kept": 0}
    seen: dict = {}
    shard_files = sorted(
        f for f in os.listdir(teacher_dir) if f.startswith("shard-") and f.endswith(".jsonl")
    )
    rows = []
    for name in shard_files:
        with open(os.path.join(teacher_dir, name), encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                counts["input"] += 1
                row = json.loads(line)
                try:
                    pred = json.loads(row["teacher_raw"])
                except (json.JSONDecodeError, TypeError):
                    counts["a_invalid_json"] += 1
                    continue
                if not isinstance(pred, dict) or set(pred) != KEYS:
                    counts["b_wrong_keys"] += 1
                    continue
                if pred["intent"] not in intents:
                    counts["c_bad_intent"] += 1
                    continue
                text_lower = row["text"].lower()
                bad_slot = any(
                    v is not None and (not isinstance(v, str) or v.lower().strip() not in text_lower)
                    for k, v in pred.items() if k != "intent"
                )
                if bad_slot:
                    counts["d_bad_slot"] += 1
                    continue
                key = (row["id"], row["text"])
                if key in seen:
                    counts["e_duplicate"] += 1
                    continue
                seen[key] = True
                rows.append({"id": row["id"], "text": row["text"], **pred})
                counts["kept"] += 1
    rows.sort(key=lambda r: r["id"])
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "train.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    digest = hashlib.sha256(open(out_path, "rb").read()).hexdigest()
    with open(os.path.join(out_dir, "train.sha256"), "w", encoding="utf-8") as f:
        f.write(f"{digest}  train.jsonl\n")
    counts["sha256"] = digest
    return counts


if __name__ == "__main__":
    result = clean(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
    assert result["input"] == (result["a_invalid_json"] + result["b_wrong_keys"]
                               + result["c_bad_intent"] + result["d_bad_slot"]
                               + result["e_duplicate"] + result["kept"]), "counts do not balance"
