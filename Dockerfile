FROM python:3.10-slim

# Install FFmpeg and system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create necessary folders
RUN mkdir -p downloads

# Port exposure
EXPOSE 10000

# Start command (using gunicorn for web and python for bot)
CMD python3 main.py
