FROM python:3.10-alpine

WORKDIR /app

# Install required packages
RUN apk add --no-cache \
    docker \
    docker-cli \
    bash \
    curl \
    git \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev

# Copy application files
COPY requirements.txt .
COPY run.sh .
COPY config.yaml .
COPY templates/ ./templates/
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Add entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose port for web server
EXPOSE 5050

# Set environment variables
ENV CONFIG_PATH=/app/config.yaml
ENV OUTPUT_DIR=/data
ENV CONFIG_REPO=
ENV CHECK_INTERVAL=60
ENV MODE=extract
ENV PYTHONUNBUFFERED=1

# Create volume for output data
VOLUME ["/data"]

ENTRYPOINT ["/docker-entrypoint.sh"] 