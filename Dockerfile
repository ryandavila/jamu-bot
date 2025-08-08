FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies from pyproject.toml using uv.lock
RUN uv sync --no-extra dev --no-editable

# Copy application code
COPY . .

CMD ["uv", "run", "bot.py"]
