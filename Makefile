# CS3081 mini project — run targets in dependency order.
# Rule: never run Ollama + k3d + training at the same time (8 GB RAM).
# See README.md. All paths are relative to the repo root.

.PHONY: cluster down label clean train up test eval loadtest

cluster:  ## Phase A: create k3d cluster + SeaweedFS, create buckets
	k3d cluster create --config cluster/k3d.yaml
	kubectl apply -f deploy/seaweedfs.yaml
	@echo "Create buckets datasets + models in the SeaweedFS filer, then upload student_kit/data/commands_pool.jsonl to datasets/"

down:  ## Stop everything (cluster + Ollama) to free RAM before training
	k3d cluster delete cs3081 || true
	osascript -e 'quit app "Ollama"' 2>/dev/null || pkill -f ollama || true

label:  ## Phase A: teacher labelling (Ollama on laptop, 2 workers)
	ollama pull phi3.5
	SHARD_COUNT=2 SHARD_INDEX=0 python3 worker/worker.py & SHARD_COUNT=2 SHARD_INDEX=1 python3 worker/worker.py & wait

clean:  ## Phase A: rejection rules (a)-(e) -> datasets/v1/train.jsonl
	python3 worker/clean.py datasets/teacher datasets/v1

train:  ## Phase B: train student (SUBSET=50 smoke test supported)
	python3 training/train.py --config training/config.yaml $(if $(SUBSET),--subset $(SUBSET))

up:  ## Phases C/D: build + deploy everything from a fresh clone
	k3d cluster create --config cluster/k3d.yaml
	kubectl apply -f deploy/seaweedfs.yaml
	kubectl rollout status deployment/seaweedfs -n data --timeout=180s
	docker build -t student-service:v1 -f service/Dockerfile .
	docker tag student-service:v1 parser:v1
	k3d image import parser:v1 -c cs3081
	kubectl create namespace app --dry-run=client -o yaml | kubectl apply -f -
	kubectl create secret generic s3-creds -n app --from-literal=access-key=test --from-literal=secret-key=test --dry-run=client -o yaml | kubectl apply -f -
	./scripts/setup_s3.sh
	kubectl apply -f deploy/app.yaml
	kubectl rollout status deployment/parser -n app --timeout=300s

test:  ## Unit tests (CI needs >= 3)
	python3 -m pytest tests/ -q

eval:  ## Phase B: score predictions against validation (gate: validity >= 95)
	python3 student_kit/tools/score.py results/predictions.jsonl student_kit/data/validation.jsonl --out results/score.json --min-validity 95

loadtest:  ## Phase F: standard Locust run through the Ingress
	LOADTEST_TEXTS=student_kit/data/validation.jsonl locust -f student_kit/tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time 2m --host http://localhost:8080 --csv results/loadtest
