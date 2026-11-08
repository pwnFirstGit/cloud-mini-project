# Report outline — max 8 pages, one section per task

1. Task 1 — Teacher labelling + cleaning: worker sharding rule, prompt,
   counts table (input = (a)+(b)+(c)+(d)+duplicates+kept), train.sha256.
2. Task 2 — Training + evaluation: config (seed/LR/batch/epochs/max-len/
   library versions), loss curve, score.py table for teacher / untrained
   pythia-70m / student v1 / v2, ≤1-page distillation explanation
   (sequence-level vs logit-based; why logit-based is impossible here —
   Ollama gives text only, no teacher logits; one real limitation).
3. Task 3 — Service: endpoints, env config, schema validation + 500 rule,
   50-request sequential test at 1 CPU / 1 GiB with peak memory.
4. Task 4 — Deployment + reliability: rolling update v1→v2 (≤0.5%
   failures), rollback, Pod deletion (≤2%), cold start (median of 3),
   load balancing (each replica ≥30%). State clearly: a single-node
   laptop cluster proves nothing about multi-machine fault tolerance.
5. Task 5 — Subnets + NACL: table from network/subnets.md, nacl.json
   rules, `nacl_sim.py --check` 6/6, half-page stateless explanation.
6. Task 6 — CI/CD: pipeline order, gate result, failing-run link
   (untrained model), gitleaks clean, AI_USE.md.
7. Task 7 — Measurement + cost: Locust p50/p95/throughput/error rate,
   `kubectl top pods`, cost per 1,000 requests from rate_card.json
   (₹3.50/vCPU-hour + ₹0.45/GiB-hour, billed on limits), one SLO with
   target + window + error budget in requests, 6-row review table with a
   measured number in every row.
