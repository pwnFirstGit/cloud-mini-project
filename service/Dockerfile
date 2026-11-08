# CPU-only image, no model weights inside (downloaded at startup from
# SeaweedFS). Keep <= 2 GB: slim base + CPU torch index only.
FROM python:3.11-slim
WORKDIR /app
COPY service/requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1 && \
    pip install --no-cache-dir -r requirements.txt
COPY service/app.py service/validate.py .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
