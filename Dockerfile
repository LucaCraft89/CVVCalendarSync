# Use the official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install cron and cleanup
RUN apt-get update && \
    apt-get install -y cron && \
    rm -rf /var/lib/apt/lists/*

# Copy application files
COPY classevivaSync.py .
COPY healthcheck.py .
COPY cronjob /etc/cron.d/classeviva-cron

# Apply permissions
RUN chmod 0644 /etc/cron.d/classeviva-cron && \
    chmod +x ./classevivaSync.py && \
    chmod +x ./healthcheck.py

# Apply the cron job to the crontab
RUN crontab /etc/cron.d/classeviva-cron

# Create log directory
RUN mkdir -p /var/log/classeviva

# Health check
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s --retries=3 \
    CMD python3 /app/healthcheck.py || exit 1

# Run initial sync on container start, then start cron
CMD python3 /app/classevivaSync.py && cron -f
