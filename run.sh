#!/bin/bash

# Docker Binary Extractor - Run Script
# This script runs the Docker Binary Extractor application

# Default values
CONFIG_FILE="config.yaml"
OUTPUT_DIR="extracted_binaries"
MODE="both"
PORT=5050
INTERVAL=60

# Help function
show_help() {
    echo "Docker Binary Extractor"
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -c, --config FILE     Configuration file (default: config.yaml)"
    echo "  -o, --output DIR      Output directory (default: extracted_binaries)"
    echo "  -r, --repo URL        GitHub repository URL for configuration"
    echo "  -i, --interval SEC    Check interval in seconds (default: 60)"
    echo "  -p, --port PORT       Web server port (default: 5050)"
    echo "  -m, --mode MODE       Operation mode: extract, web, or both (default: both)"
    echo "  -h, --help            Show this help message"
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -r|--repo)
            GITHUB_REPO="$2"
            shift 2
            ;;
        -i|--interval)
            INTERVAL="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
done

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Activated virtual environment"
fi

# Build command
CMD="python src/main.py --config $CONFIG_FILE --output $OUTPUT_DIR --interval $INTERVAL --port $PORT --mode $MODE"

# Add repo if specified
if [ -n "$GITHUB_REPO" ]; then
    CMD="$CMD --repo $GITHUB_REPO"
fi

# Run the application
echo "Starting Docker Binary Extractor..."
echo "Mode: $MODE"
echo "Config: $CONFIG_FILE"
echo "Output: $OUTPUT_DIR"
echo "Port: $PORT"
echo "Interval: $INTERVAL"
if [ -n "$GITHUB_REPO" ]; then
    echo "Repository: $GITHUB_REPO"
fi
echo

# Execute the command
exec $CMD 