#!/bin/bash
set -e

# Check if Docker socket is mounted
if [ ! -S /var/run/docker.sock ]; then
    echo "ERROR: Docker socket not mounted. Please mount the Docker socket to /var/run/docker.sock"
    echo "Example: docker run -v /var/run/docker.sock:/var/run/docker.sock ..."
    exit 1
fi

# Make output directory if it doesn't exist
mkdir -p ${OUTPUT_DIR}

# Set up command line arguments based on environment variables
ARGS="--config ${CONFIG_PATH} --output ${OUTPUT_DIR} --interval ${CHECK_INTERVAL}"

# Add repository argument if provided
if [ -n "${CONFIG_REPO}" ]; then
    ARGS="${ARGS} --repo ${CONFIG_REPO}"
fi

# Run in the specified mode
if [ "${MODE}" = "web" ]; then
    echo "Starting web server on port 5050..."
    exec python /app/web_server.py 5050
elif [ "${MODE}" = "extract" ]; then
    echo "Starting binary extractor..."
    echo "Configuration path: ${CONFIG_PATH}"
    echo "Output directory: ${OUTPUT_DIR}"
    if [ -n "${CONFIG_REPO}" ]; then
        echo "Configuration repository: ${CONFIG_REPO}"
    fi
    echo "Check interval: ${CHECK_INTERVAL} seconds"
    exec python /app/docker_extractor.py ${ARGS}
elif [ "${MODE}" = "both" ]; then
    echo "Starting binary extractor in background..."
    python /app/docker_extractor.py ${ARGS} &
    
    echo "Starting web server on port 5050..."
    exec python /app/web_server.py 5050
else
    echo "Invalid MODE value: ${MODE}"
    echo "Valid values are: extract, web, both"
    exit 1
fi 