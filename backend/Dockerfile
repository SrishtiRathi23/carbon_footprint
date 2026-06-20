# Container image for Cloud Run.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY . .

# Cloud Run provides $PORT; default to 8080 for local runs.
ENV PORT=8080
EXPOSE 8080

# Run a single worker; Cloud Run scales by instances, not in-process workers.
CMD exec uvicorn app:app --host 0.0.0.0 --port ${PORT}
