# Dockerfile

# Build stage
FROM python:3.11-slim-bookworm as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the pip requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Runtime stage
FROM python:3.11-slim-bookworm

# Install runtime system dependencies (including ffmpeg)
RUN apt-get update && apt-get install -y \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create an application user and switch to that user
RUN useradd --create-home appuser
WORKDIR /app
USER appuser

# Copy installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the rest of the application code
COPY . .

# Download required NLTK data
RUN python -m nltk.downloader punkt stopwords

# Set runtime environment variables
ENV PORT=5000 \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

EXPOSE $PORT

# Health check for Heroku
HEALTHCHECK --interval=30s --timeout=10s \
  CMD curl -f http://localhost:$PORT/health || exit 1

# Entrypoint command
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
