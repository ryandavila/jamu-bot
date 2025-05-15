FROM python:3.13-slim

WORKDIR /app

COPY . .

# Install build dependencies for potential native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc \
  libc6-dev \
  && rm -rf /var/lib/apt/lists/* \
  && pip install --no-cache-dir -r requirements.txt \
  && apt-get purge -y --auto-remove gcc libc6-dev

CMD ["python", "bot.py"]