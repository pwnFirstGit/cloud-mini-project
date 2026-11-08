"""Teacher labelling worker (Task 1).

Takes the shard of commands_pool.jsonl whose 0-based line number mod
SHARD_COUNT equals SHARD_INDEX, asks the Phi-3.5 teacher (Ollama on the
laptop, temperature 0, seed 42) for the 4-key JSON, and writes replies
EXACTLY as generated — no manual edits — to
datasets/teacher/shard-N.jsonl as {"id", "text", "teacher_raw"}.

Run at least 2 workers with different SHARD_INDEX values (see Makefile).
Ollama must be running on the laptop; OLLAMA_HOST defaults to
http://localhost:11434. If workers run inside the cluster, set OLLAMA_HOST
to http://host.docker.internal:11434 instead.

Resilience (added 2026-11-07 after both Jobs crash-looped on 300s
ReadTimeouts): ask_teacher retries 3 times with a 1200s timeout, and
main() resumes from an existing shard file instead of rewriting it, so a
pod crash loses at most the in-flight line. The shard file must live on
a PersistentVolumeClaim (deploy/teacher-out-pvc.yaml, mounted at
/app/datasets/teacher) for resume to survive a pod crash. On completion
the shard is uploaded to s3://datasets/teacher/shard-N.jsonl when
S3_ENDPOINT is set.
"""
import json
import os
import sys
import time

import requests

MODEL = os.environ.get("TEACHER_MODEL", "phi3.5")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
SHARD_COUNT = int(os.environ.get("SHARD_COUNT", "2"))
SHARD_INDEX = int(os.environ.get("SHARD_INDEX", "0"))
POOL = os.environ.get("POOL", "student_kit/data/commands_pool.jsonl")
OUT_DIR = os.environ.get("TEACHER_OUT", "datasets/teacher")

with open("prompts/teacher_prompt.txt", encoding="utf-8") as f:
    PROMPT_TEMPLATE = f.read()


def ask_teacher(command: str) -> str:
    last_err = None
    for attempt in range(1, 4):
        try:
            resp = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": MODEL,
                    "prompt": PROMPT_TEMPLATE.format(command=command),
                    "stream": False,
                    "options": {"temperature": 0, "seed": 42},
                },
                timeout=1200,
            )
            resp.raise_for_status()
            return resp.json()["response"]
        except requests.exceptions.RequestException as e:
            last_err = e
            print(f"attempt {attempt}/3 failed ({type(e).__name__}), retrying in 10s", flush=True)
            time.sleep(10)
    raise last_err


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"shard-{SHARD_INDEX}.jsonl")
    done = set()
    if os.path.exists(out_path):
        valid = []
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["id"])
                    valid.append(line)
                except json.JSONDecodeError:
                    pass
        with open(out_path, "w", encoding="utf-8") as f:
            f.writelines(valid)
    print(f"shard {SHARD_INDEX}: resuming with {len(done)} already done", flush=True)
    n = 0
    with open(POOL, encoding="utf-8") as fin, open(out_path, "a", encoding="utf-8") as fout:
        for line_no, line in enumerate(fin):
            if line_no % SHARD_COUNT != SHARD_INDEX:
                continue
            row = json.loads(line)
            if row["id"] in done:
                continue
            raw = ask_teacher(row["text"])
            fout.write(json.dumps({"id": row["id"], "text": row["text"], "teacher_raw": raw}) + "\n")
            fout.flush()
            n += 1
            if n % 50 == 0:
                print(f"shard {SHARD_INDEX}: {len(done) + n} done", flush=True)
    print(f"shard {SHARD_INDEX}/{SHARD_COUNT} written to {out_path}")
    if os.environ.get("S3_ENDPOINT"):
        import boto3
        s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"],
                          aws_access_key_id=os.environ["S3_ACCESS_KEY"],
                          aws_secret_access_key=os.environ["S3_SECRET_KEY"])
        s3.upload_file(out_path, os.environ.get("S3_BUCKET", "datasets"),
                       f"teacher/shard-{SHARD_INDEX}.jsonl")
        print(f"shard {SHARD_INDEX}/{SHARD_COUNT} uploaded to s3://datasets/teacher/shard-{SHARD_INDEX}.jsonl")


if __name__ == "__main__":
    sys.exit(main())
