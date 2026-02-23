FROM python:3.11-slim

WORKDIR /app

# Install required system libs (needed for PIL / OCR deps if any light ones)
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Railway uses dynamic PORT env
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}