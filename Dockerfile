FROM python:3.13-slim

WORKDIR /app

# System deps for feedparser + httpx
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user
RUN useradd -m -u 1001 hermes && chown -R hermes:hermes /app
USER hermes

# Railway (and most PaaS) assign a dynamic $PORT and route external traffic to it.
# Binding to a hardcoded 8080 makes the app unreachable -> 502 "Application failed to
# respond" (the container is up but not listening where the platform routes). Bind to
# $PORT, falling back to 8080 for local `docker run`.
ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
    CMD curl -f "http://localhost:${PORT}/health" || exit 1

# Shell form so $PORT expands at runtime (exec/JSON form would pass the literal string).
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
