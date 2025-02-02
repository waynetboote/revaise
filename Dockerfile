# Dockerfile
# Build stage
FROM python:3.11-slim-bookworm as builder

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.0

# Project setup
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Runtime stage
FROM python:3.11-slim-bookworm

# Runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Application user
RUN useradd --create-home appuser
WORKDIR /app
USER appuser

# Copy dependencies
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Application files
COPY --chown=appuser:appuser . .

# NLTK data
RUN python -m nltk.downloader punkt stopwords

# Runtime config
ENV PORT=5000 \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s \
  CMD curl -f http://localhost:$PORT/health || exit 1

# Entrypoint
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
