# Multi-stage lightweight secure Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install security certificates & curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements & install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and UI assets
COPY app.py .
COPY static/ ./static/

# Environment settings
ENV PORT=8080
ENV REQUIRE_PIN=true
ENV SHARE_PIN=1234
ENV PYTHONUNBUFFERED=1

# Expose server port
EXPOSE 8080

# Run DropSync Pro
CMD ["python", "app.py"]
