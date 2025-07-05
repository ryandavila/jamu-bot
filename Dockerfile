FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files first for better caching
COPY pyproject.toml ./

# Install dependencies only
RUN uv pip install --system --no-cache discord.py>=2.3.2 python-dotenv>=1.0.0 aiosqlite>=0.19.0

# Copy application code
COPY . .

CMD ["python", "bot.py"]