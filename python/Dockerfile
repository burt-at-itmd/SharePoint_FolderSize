# Python implementation Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY sharepoint_folder_size.py .
COPY health_check.py .

# Make scripts executable
RUN chmod +x sharepoint_folder_size.py health_check.py

# Create output directory
RUN mkdir -p /output

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Add health check
HEALTHCHECK --interval=5m --timeout=30s --start-period=1m --retries=3 \
  CMD python health_check.py \
    --tenant-id="${TENANT_ID}" \
    --client-id="${CLIENT_ID}" \
    --site-url="${SITE_URL}" \
    || exit 1

# Default command (show help)
CMD ["python", "sharepoint_folder_size.py", "--help"]