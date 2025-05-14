#!/bin/bash
set -e

# Check if Docker socket is mounted
if [ ! -S /var/run/docker.sock ] && [ "${MODE}" != "web" ]; then
    echo "ERROR: Docker socket not mounted. Please mount the Docker socket to /var/run/docker.sock"
    echo "Example: docker run -v /var/run/docker.sock:/var/run/docker.sock ..."
    exit 1
fi

# Check Docker socket permissions if we're in extract mode
if [ "${MODE}" != "web" ] && [ ! -w /var/run/docker.sock ]; then
    echo "WARNING: Docker socket is not writable by the current user"
    echo "This may cause permission issues when extracting binaries"
    echo "Try: chmod 666 /var/run/docker.sock on the host machine"
fi

# Make output directory if it doesn't exist
mkdir -p ${OUTPUT_DIR}

# Ensure output directory is writable
if [ ! -w ${OUTPUT_DIR} ]; then
    echo "ERROR: Output directory (${OUTPUT_DIR}) is not writable"
    echo "Please ensure the directory has the correct permissions"
    exit 1
fi

# Set up command line arguments based on environment variables
ARGS="--config ${CONFIG_PATH} --output ${OUTPUT_DIR} --interval ${CHECK_INTERVAL} --mode ${MODE}"

# Add repository argument if provided
if [ -n "${CONFIG_REPO}" ]; then
    ARGS="${ARGS} --repo ${CONFIG_REPO}"
fi

# Add port argument if specified
if [ -n "${PORT}" ]; then
    ARGS="${ARGS} --port ${PORT}"
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
echo "Platform support: ${DOCKER_PLATFORM_SUPPORT:-true}"

exec python /app/src/main.py ${ARGS} 