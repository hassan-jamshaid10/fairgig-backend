FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files first (layer caching)
COPY pyproject.toml .
RUN uv sync --no-dev

# Copy source
COPY . .

ENV PYTHONPATH=/app
