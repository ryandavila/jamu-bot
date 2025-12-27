FROM python:3.14.2-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies from pyproject.toml using uv.lock (exclude dev dependencies)
RUN uv sync --no-dev --no-editable

# Copy application code
COPY . .

CMD ["uv", "run", "python", "-m", "bot.main"]
