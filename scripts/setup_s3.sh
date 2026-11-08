#!/bin/bash
set -e
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test
kubectl port-forward -n data svc/seaweedfs 8333:8333 >/tmp/portforward_s3.log 2>&1 &
PF_PID=$!
trap "kill $PF_PID 2>/dev/null || true" EXIT
sleep 5
aws --endpoint-url http://localhost:8333 s3 mb s3://datasets || true
aws --endpoint-url http://localhost:8333 s3 mb s3://models || true
if [ -f student_kit/data/commands_pool.jsonl ]; then
  aws --endpoint-url http://localhost:8333 s3 cp student_kit/data/commands_pool.jsonl s3://datasets/commands_pool.jsonl
fi
if [ ! -f models/v1/model.safetensors ]; then
  echo "Downloading model v1 from GitHub Release..."
  gh release download v1 --pattern 'model-v1.tar.gz' --dir /tmp
  mkdir -p models/v1
  tar -xzf /tmp/model-v1.tar.gz -C models/v1
fi
aws --endpoint-url http://localhost:8333 s3 sync models/v1 s3://models/v1
aws --endpoint-url http://localhost:8333 s3 ls s3://models/v1/
echo "S3 setup done"
