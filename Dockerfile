# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8321 \
    MCP_API_KEY=""

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# NEW CLEAN STRUCTURE - Everything in backend/
# ============================================
COPY backend/ ./backend/
COPY prompts/ ./prompts/

RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

RUN mkdir -p /app/data && chown appuser:appuser /app/data

EXPOSE 8321

# Health check (FIXED)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8321/', timeout=5)" || exit 1

CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8321"]