# Mend AI Red Teaming Bridge - Docker Image
FROM python:3.15-alpine

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    curl \
    gcc \
    musl-dev \
    libffi-dev

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY adapter.py .
COPY config.yml .

# Create a non-root user for security
RUN adduser -D -s /bin/sh bridge
RUN chown -R bridge:bridge /app
USER bridge

# Expose the port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "main.py"] 