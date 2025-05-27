FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install build dependencies for potential native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc \
  libc6-dev \
  && rm -rf /var/lib/apt/lists/* \
  && uv pip install --system --no-cache -e . \
  && apt-get purge -y --auto-remove gcc libc6-dev

# Copy application code
COPY . .

CMD ["python", "bot.py"]