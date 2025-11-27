FROM python:3.11-slim

# Install system dependencies for crawl4ai and Playwright
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY mamcrawler/ ./mamcrawler/
COPY backend/ ./backend/
COPY *.py ./

# Create directory for state files
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Health check configuration
# Docker will use this to determine if the container is healthy
# Checks every 30 seconds, with 3 second timeout, starts after 40 seconds
# Container is unhealthy after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the downloader
CMD ["python", "mam_audiobook_qbittorrent_downloader.py"]

