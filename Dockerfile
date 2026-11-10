# ── Stage 1: build dependencies ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: production image ─────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application source
COPY research_agent/ ./research_agent/
COPY webapp/         ./webapp/
COPY run.py          .
COPY env.example     .

# Create outputs directory
RUN mkdir -p outputs

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# IBM Code Engine injects PORT; default to 8080
ENV PORT=8080

EXPOSE 8080

# Use gunicorn for production
CMD gunicorn \
      --bind "0.0.0.0:${PORT}" \
      --workers 2 \
      --threads 4 \
      --timeout 300 \
      --keep-alive 5 \
      --access-logfile - \
      --error-logfile - \
      webapp.app:app
