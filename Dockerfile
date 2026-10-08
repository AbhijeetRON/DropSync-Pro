# Secure Multi-Stage Dockerfile for DropSync Pro
# Follows CIS benchmarks: Non-root user, minimal base, read-only rootfs compatibility

FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final minimal production image
FROM python:3.12-slim

# Create dedicated non-root user & group
RUN groupadd -g 10001 dropsync && \
    useradd -u 10001 -g dropsync -s /bin/sh -m dropsync

WORKDIR /app

# Copy python dependencies from builder
COPY --from=builder /root/.local /home/dropsync/.local
ENV PATH=/home/dropsync/.local/bin:$PATH

# Copy application files
COPY --chown=dropsync:dropsync app.py config_manager.py ./
COPY --chown=dropsync:dropsync static/ ./static/

# Prepare writable shared data directory
RUN mkdir -p /app/shared_data && chown -R dropsync:dropsync /app

# Switch to non-root user
USER dropsync

# Security & environment defaults
ENV PORT=8080
ENV REQUIRE_PIN=true
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Built-in Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/status')" || exit 1

ENTRYPOINT ["python", "app.py"]
