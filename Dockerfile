# ── Stage 1: install dependencies ─────────────────────────────────────────────
# Using a separate stage avoids re-downloading packages on every code change.
FROM python:3.10-slim AS deps

WORKDIR /deps

# Install OS-level build tools needed by some Python packages (e.g. pymupdf, chromadb)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ─────────────────────────────────────────────────────
FROM python:3.10-slim AS runtime

# Copy OS libs needed at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from the build stage
COPY --from=deps /install /usr/local

WORKDIR /app

# Copy application source
COPY app/ ./app/

# Non-root user for security
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# ChromaDB will write to /app/data/chroma — Docker Compose mounts a volume here.
# /app/uploads is used as a staging area when ingesting directories via docker cp.
RUN mkdir -p /app/data/chroma /app/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
