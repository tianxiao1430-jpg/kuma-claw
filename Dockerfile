FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY pyproject.toml requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home kuma && \
    mkdir -p /home/kuma/.kuma-claw && \
    chown -R kuma:kuma /home/kuma /app

USER kuma

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health').raise_for_status()" || exit 1

EXPOSE 8080

ENTRYPOINT ["python", "-m", "kuma_claw.main"]
CMD ["--web"]
