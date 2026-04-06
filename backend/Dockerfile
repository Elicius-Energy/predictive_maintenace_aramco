FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for scipy/numpy/faiss
RUN apt-get update && apt-get install -y \
    build-essential \
    libopenblas-dev \
    libomp-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory
RUN mkdir -p data/knowledge data/sample_data

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
