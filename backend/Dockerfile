# ============================================================
# Backend Dockerfile — Python 3.11 + FastAPI
# ============================================================

FROM python:3.11-slim AS backend

WORKDIR /app

# System deps: JDK 19 for Joern + asyncpg native build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc libpq-dev curl wget unzip \
        openjdk-19-jre-headless && \
    rm -rf /var/lib/apt/lists/*

# Install Joern CLI (pinned to a known-good version)
RUN curl -L "https://github.com/joernio/joern/releases/latest/download/joern-install.sh" \
        -o /tmp/joern-install.sh && \
    chmod +x /tmp/joern-install.sh && \
    /tmp/joern-install.sh --install-dir /opt/joern --no-interactive && \
    rm /tmp/joern-install.sh
ENV PATH="/opt/joern/joern-cli:$PATH"


# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application code
COPY backend/ /app/backend/
COPY .env /app/.env
COPY uploads/ /app/uploads/

# Create logs directory
RUN mkdir -p /app/logs

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
