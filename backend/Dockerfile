# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for scipy/numpy/faiss
RUN apt-get update && apt-get install -y \
    build-essential \
    libopenblas-dev \
    libomp-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install torch --index-url https://download.pytorch.org/whl/cpu && \
    PYTHONPATH=/install/lib/python3.11/site-packages pip install --no-cache-dir --prefix=/install -r requirements.txt

# Pre-download the sentence-transformer model
RUN PYTHONPATH=/install/lib/python3.11/site-packages python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libopenblas0 \
    libomp5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages
COPY --from=builder /install /usr/local

# Copy pre-downloaded model cache
COPY --from=builder /root/.cache/huggingface /home/appuser/.cache/huggingface

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -s /sbin/nologin appuser

COPY . .

# Create required directories
RUN mkdir -p data/knowledge data/sample_data data/logs \
    && chown -R appuser:appuser /app /home/appuser

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
