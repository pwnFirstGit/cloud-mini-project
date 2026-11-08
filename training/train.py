"""Train the pythia-70m student on teacher labels (Task 2, CPU only).

Format per example: "Command: <cmd> JSON: <teacher JSON>".
Saves per-epoch loss to training/loss.csv and the model to output_dir.
Usage: python3 training/train.py --config training/config.yaml [--subset 50]
`make train SUBSET=50` must work from a fresh clone — the assessor runs it.
"""
import argparse
import csv
import json
import os

import torch
import yaml
from transformers import (AutoModelForCausalLM, AutoTokenizer, Trainer,
                          TrainingArguments)


def load_examples(train_file: str, subset: int | None, cap: int) -> list[str]:
    limit = subset if subset is not None else cap
    texts = []
    with open(train_file, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            label = {"intent": row["intent"], "date": row["date"],
                     "time": row["time"], "place": row["place"]}
            texts.append(f"Command: {row['text']} JSON: {json.dumps(label)}")
            if len(texts) >= limit:
                break
    return texts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="training/config.yaml")
    ap.add_argument("--subset", type=int, default=None)
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    torch.manual_seed(cfg["seed"])
    tok = AutoTokenizer.from_pretrained(cfg["model"])
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    texts = load_examples(cfg["train_file"], args.subset, cfg.get("max_train_rows", 1500))
    enc = tok(texts, truncation=True, max_length=cfg["max_seq_len"],
              padding=True, return_tensors="pt")
    enc["labels"] = enc["input_ids"].clone()

    class DS(torch.utils.data.Dataset):
        def __len__(self):
            return len(texts)

        def __getitem__(self, i):
            return {k: v[i] for k, v in enc.items()}

    model = AutoModelForCausalLM.from_pretrained(cfg["model"])
    out = cfg["output_dir"]
    trainer = Trainer(
        model=model, train_dataset=DS(),
        args=TrainingArguments(
            output_dir=out, per_device_train_batch_size=cfg["batch_size"],
            num_train_epochs=cfg["epochs"], learning_rate=cfg["learning_rate"],
            seed=cfg["seed"], logging_steps=10, save_strategy="no",
            report_to=[], use_cpu=True),
    )
    trainer.train()
    model.save_pretrained(out)
    tok.save_pretrained(out)
    os.makedirs("training", exist_ok=True)
    # One value per epoch (the marking table checks this): average the
    # per-step logged losses within each epoch.
    from collections import defaultdict
    import math
    by_epoch: dict = defaultdict(list)
    for entry in trainer.state.log_history:
        if "loss" in entry and "epoch" in entry:
            # log_history stores the fractional epoch completed (0.05 is
            # 5% through epoch 1), so the epoch number is the ceiling.
            by_epoch[math.ceil(entry["epoch"])].append(entry["loss"])
    with open("training/loss.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "loss"])
        for ep in sorted(by_epoch):
            losses = by_epoch[ep]
            w.writerow([ep, sum(losses) / len(losses)])
    print(f"saved to {out}; loss history in training/loss.csv")


if __name__ == "__main__":
    main()
