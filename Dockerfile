FROM python:3.11-slim

# Prevent Python buffering
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install basic system deps (safe minimal set)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (cache layer)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Railway provides PORT env var
CMD ["./start.sh"]
