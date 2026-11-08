# Labelling worker image (optional in-cluster path, Task 1).
# The Makefile `label` target runs workers on the laptop instead — use
# this image only if running workers as Jobs (deploy/pipeline-worker.yaml).
# Mount commands_pool.jsonl at /app/student_kit/data/commands_pool.jsonl
# and set OLLAMA_HOST to http://host.docker.internal:11434.
FROM python:3.11-slim
WORKDIR /app
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker/worker.py .
COPY prompts/teacher_prompt.txt prompts/teacher_prompt.txt
CMD ["python3", "worker.py"]
