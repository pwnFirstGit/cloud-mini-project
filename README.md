# Cloud Computing (CS3081) — Mini Project

Sequence-level knowledge distillation: Phi-3.5-mini-instruct (teacher)
→ EleutherAI/pythia-70m (student) parsing SLURP commands into 4-key JSON,
deployed as a FastAPI service on a local k3d cluster with SeaweedFS.

**Disclosure:** labelling and training ran on Kaggle GPU (T4 x2) via Hugging Face
transformers, not Ollama/CPU — same model, prompt, temperature 0, seed 42.
The repo code is CPU-based and `make train` runs on CPU. See report §1–2.

## Commands — build, deploy, test, tear down

```bash
make cluster   # build: create k3d cluster + SeaweedFS, buckets datasets + models
make up        # build + deploy: image, secret, S3 models, app.yaml, rollout (<=3 commands from a fresh clone)
make test      # test: unit tests
make eval      # test: score.py on validation, quality gate --min-validity 95
make loadtest  # test: Locust, 4 users, 2 min, through Ingress http://localhost:8080
make down      # tear down: delete cluster, stop Ollama
```

## Machine rules (MacBook M1 Air, 8 GB RAM, 46 GB free)

**Never run Ollama, the k3d cluster, and training at the same time.**
Each fits alone (~2–2.5 GB); any two together are marginal, all three will
thrash. The assignment allows training and deployment to be done separately —
use that. Keep ≥10 GB free disk (macOS needs it for swap); run
`docker system prune` between phases.

## Phase 0 — tools (1–2 hrs, do this first)

Install: Homebrew, Docker Desktop (Apple Silicon build, memory 3 GB,
disk image ~20 GB), Ollama, k3d, kubectl, Python 3.11 (arm64), git, `gh` CLI.
Then copy the verified student kit into this repo root as `student_kit/`
(it is already verified at `~/workspace/student_kit/` — 3,000 commands
C0001–C3000, 100 validation rows, schema, rate card ₹3.50/vCPU-hour +
₹0.45/GiB-hour). Read `student_kit/tools/score.py -h` and
`student_kit/tools/nacl_sim.py -h` before starting.

```bash
cp -r ~/workspace/student_kit ./student_kit   # on the Mac, from this workspace
make cluster   # Phase A: k3d + SeaweedFS, buckets datasets + models
make label     # Phase A: teacher labelling (runs 1–3 hrs; run overnight)
make clean     # Phase A: rejection rules (a)–(e) -> datasets/v1/train.jsonl
make down      # stop cluster + Ollama before training
make train     # Phase B: student training (repo code CPU only; the run in this
               # submission used Kaggle GPU, see disclosure above)
make train SUBSET=50   # smoke test — the assessor will run this
make up        # Phase C/D: rebuild + deploy from a fresh clone (<=3 commands)
```

## Phases (dependency order)

- **A — Task 1:** labelling + `clean.py`. Counts must balance:
  input = (a)+(b)+(c)+(d)+duplicates+kept. Re-running `clean.py` must
  reproduce `train.sha256`.
- **B — Task 2:** train v1, train v2 (one more epoch or another seed),
  `score.py` on validation for teacher / untrained pythia-70m / student.
- **C — Task 3:** FastAPI service (`service/`), 50-request sequential test
  at 1 CPU / 1 GiB, record peak memory.
- **D — Task 4:** rolling update v1→v2 (≤0.5% failures), rollback, Pod
  deletion (≤2% failures), cold start (median of 3), load balancing
  (each of 2 replicas ≥30% of successes).
- **E — Task 6:** CI (lint → unit tests → model eval → gate
  `score.py --min-validity 95`), one deliberate failing run with the
  untrained model, gitleaks clean, `AI_USE.md`.
- **F — Task 7:** Locust through the Ingress, cost from `rate_card.json`
  (billed on CPU/memory **limits**), one SLO + error budget, 6-row
  review table with a measured number in every row.
- **G — submission:** `report/report.pdf` (max 8 pages, one section per
  task), handwritten reflection scanned as `<roll_number>.pdf`
  (exact name — wrong name = zero for it), tag final commit `final`.

## Layout

`cluster/` k3d config · `prompts/` teacher prompt · `worker/` labelling
worker + `clean.py` · `training/` config + train script ·
`service/` FastAPI app + Dockerfile · `deploy/` k8s manifests ·
`network/` subnets + NACL · `.github/workflows/` CI ·
`report/` report (6 pages, one section per task) · `results/` evidence (scores, load test, logs).

Never commit model weights or secrets — weights live in SeaweedFS and as a
GitHub Release asset only. Validation data is never trained on.
