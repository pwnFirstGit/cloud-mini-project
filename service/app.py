"""FastAPI command-parser service (Task 3).

POST /parse  {"text": ...} -> only the 4-key JSON, headers X-Model-Version
              and X-Served-By (= Pod name, from HOSTNAME)
GET  /healthz -> 200 always
GET  /readyz  -> 503 until the model is loaded

Config only from env: MODEL_URI, MODEL_VERSION, S3_ENDPOINT,
MAX_NEW_TOKENS, FAULT_INJECT (1 -> output becomes "not json", which must
then fail validation). Credentials only from a Kubernetes Secret.
At startup the model + tokenizer are downloaded from SeaweedFS (S3 API).
Every output is checked against schema.json: invalid -> HTTP 500 with
exactly {"error": "invalid_model_output"}, never broken JSON with 200.
"""
import os
import re

import boto3
import torch
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from transformers import AutoModelForCausalLM, AutoTokenizer

from validate import validate as _validate

MODEL_URI = os.environ["MODEL_URI"]          # e.g. s3://models/v1
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1")
S3_ENDPOINT = os.environ["S3_ENDPOINT"]      # e.g. http://seaweedfs.data:8333
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "64"))
FAULT_INJECT = os.environ.get("FAULT_INJECT", "0") == "1"

app = FastAPI()
model = None
tokenizer = None


def _download_model() -> str:
    bucket, _, prefix = MODEL_URI.replace("s3://", "").partition("/")
    print(f"Downloading model from {MODEL_URI} via {S3_ENDPOINT}", flush=True)
    s3 = boto3.client("s3", endpoint_url=S3_ENDPOINT,
                      aws_access_key_id=os.environ["S3_ACCESS_KEY"],
                      aws_secret_access_key=os.environ["S3_SECRET_KEY"])
    local = "/tmp/model"
    os.makedirs(local, exist_ok=True)
    for obj in s3.list_objects_v2(Bucket=bucket, Prefix=prefix).get("Contents", []):
        key = obj["Key"]
        dest = os.path.join(local, os.path.relpath(key, prefix))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        s3.download_file(bucket, key, dest)
    print(f"Downloaded model files from {MODEL_URI} to {local}", flush=True)
    return local
    print(f"Downloaded model files from {MODEL_URI} to {local}", flush=True)


@app.on_event("startup")
def load_model() -> None:
    global model, tokenizer
    path = _download_model()
    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.float32)
    model.eval()




@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    if model is None:
        return JSONResponse({"status": "not ready"}, status_code=503)
    return {"status": "ready"}


@app.post("/parse")
def parse(body: dict):
    # Headers must be set on the Response object actually returned; setting
    # them on an injected `response` param is lost when a JSONResponse is
    # returned instead.
    headers = {"X-Model-Version": MODEL_VERSION,
               "X-Served-By": os.environ.get("HOSTNAME", "unknown")}
    if FAULT_INJECT:
        raw = "not json"
    else:
        prompt = f"Command: {body['text']} JSON:"
        ids = tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=MAX_NEW_TOKENS,
                                 do_sample=False, pad_token_id=tokenizer.eos_token_id)
        raw = tokenizer.decode(out[0][ids["input_ids"].shape[1]:],
                               skip_special_tokens=True).strip()
        m = re.search(r"\{.*?\}", raw, re.DOTALL)
        raw = m.group(0) if m else raw
    obj = _validate(raw)
    if obj is None:
        return JSONResponse({"error": "invalid_model_output"}, status_code=500,
                            headers=headers)
    return JSONResponse(obj, headers=headers)
