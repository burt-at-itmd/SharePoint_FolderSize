# Node.js implementation Dockerfile
FROM node:18-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy package files first for better caching
COPY package*.json ./

# Install Node.js dependencies
RUN npm install

# Copy application code
COPY sharepoint-folder-size.js .

# Make script executable
RUN chmod +x sharepoint-folder-size.js

# Create output directory
RUN mkdir -p /output

# Default command (show help)
CMD ["node", "sharepoint-folder-size.js", "--help"]