#!/bin/bash
set -e

# Check if Docker socket is mounted
if [ ! -S /var/run/docker.sock ] && [ "${MODE}" != "web" ]; then
    echo "ERROR: Docker socket not mounted. Please mount the Docker socket to /var/run/docker.sock"
    echo "Example: docker run -v /var/run/docker.sock:/var/run/docker.sock ..."
    exit 1
fi

# Make output directory if it doesn't exist
mkdir -p ${OUTPUT_DIR}

# Set up command line arguments based on environment variables
ARGS="--config ${CONFIG_PATH} --output ${OUTPUT_DIR} --interval ${CHECK_INTERVAL} --mode ${MODE}"

# Add repository argument if provided
if [ -n "${CONFIG_REPO}" ]; then
    ARGS="${ARGS} --repo ${CONFIG_REPO}"
fi

# Run the application
echo "Starting Docker Binary Extractor..."
echo "Mode: ${MODE}"
echo "Configuration path: ${CONFIG_PATH}"
echo "Output directory: ${OUTPUT_DIR}"
if [ -n "${CONFIG_REPO}" ]; then
    echo "Configuration repository: ${CONFIG_REPO}"
fi
echo "Check interval: ${CHECK_INTERVAL} seconds"

exec python /app/src/main.py ${ARGS} 