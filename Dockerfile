# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY extract_news.py .
COPY parse_news.py .
COPY run_pipeline.sh .

# Make shell script executable
RUN chmod +x run_pipeline.sh

# Create necessary directories
RUN mkdir -p /app/link_input /app/text_output /app/final_output /app/whitelist_input /app/log

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV LOCAL_MODE=false

# Create non-root user for security
RUN adduser --disabled-password --gecos '' --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Run the full pipeline
CMD ["./run_pipeline.sh"]
