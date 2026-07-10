# Enterprise Retail Sales & Supply Chain Analytics
# Dockerfile — containerises the ETL pipeline + Streamlit dashboard

FROM python:3.11-slim

# ── System deps ───────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy project source ───────────────────────────────────────────────────────
COPY src/       ./src/
COPY sql/       ./sql/
COPY dax/       ./dax/
COPY app.py     ./app.py

# data/processed/ is mounted as a volume at runtime (not baked in — it's .gitignored)
# data/raw/ is also mounted at runtime if running ETL inside the container

# ── Expose Streamlit port ─────────────────────────────────────────────────────
EXPOSE 8501

# ── Healthcheck ───────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ── Default command: launch Streamlit dashboard ───────────────────────────────
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
