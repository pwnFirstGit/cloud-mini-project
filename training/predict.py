r"""Generate validation predictions with a student model (Task 2 eval).

Mirrors service/app.py exactly: prompt "Command: <cmd> JSON:", greedy
decoding, then extracts the first {...} with a NON-greedy regex. The
trained model was never taught an end-of-sequence token, so it keeps
generating after the JSON (repeating "null}" etc.). A greedy regex
(r"\{.*\}") grabs everything up to the LAST "}" — the trailing garbage
included — and the whole string fails to parse, which is why the v2
model scored 0% despite a good loss curve. The non-greedy regex takes
only the first complete object.

Usage:
  python3 training/predict.py --model models/v1 --out results/predictions.jsonl
  python3 training/predict.py --model EleutherAI/pythia-70m --out results/predictions_untrained.jsonl
Then score with:
  python3 student_kit/tools/score.py results/predictions.jsonl student_kit/data/validation.jsonl --out results/score.json --min-validity 95
CPU only.
"""
import argparse
import json
import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gold", default="student_kit/data/validation.jsonl")
    ap.add_argument("--max-new-tokens", type=int, default=64)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.float32)
    model.eval()

    rows = [json.loads(l) for l in open(args.gold, encoding="utf-8") if l.strip()]
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            prompt = f"Command: {r['text']} JSON:"
            ids = tok(prompt, return_tensors="pt")
            with torch.no_grad():
                out = model.generate(**ids, max_new_tokens=args.max_new_tokens,
                                     do_sample=False, pad_token_id=tok.eos_token_id)
            raw = tok.decode(out[0][ids["input_ids"].shape[1]:],
                             skip_special_tokens=True).strip()
            # Non-greedy: first complete {...} only, same as service/app.py.
            m = re.search(r"\{.*?\}", raw, re.DOTALL)
            pred = m.group(0) if m else raw
            f.write(json.dumps({"id": r["id"], "prediction": pred}) + "\n")
    print(f"wrote {len(rows)} predictions to {args.out}")


if __name__ == "__main__":
    main()
