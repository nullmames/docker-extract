#!/bin/bash

# Configuration
CONFIG_FILE="config.yaml"
OUTPUT_DIR="extracted_binaries"
GITHUB_REPO="https://github.com/nullmames/docker-extract"
CHECK_INTERVAL=60

# Help function
show_help() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -c, --config FILE     Configuration file (default: config.yaml)"
    echo "  -o, --output DIR      Output directory (default: extracted_binaries)"
    echo "  -r, --repo URL        GitHub repository URL (default: none)"
    echo "  -i, --interval SEC    Check interval in seconds (default: 60)"
    echo "  -l, --local           Use only local config file (ignore repository)"
    echo "  -h, --help            Show this help message"
    exit 0
}

# Parse arguments
USE_REPO=true
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
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        -l|--local)
            USE_REPO=false
            shift
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

# Activate virtual environment
source venv/bin/activate

# Run the extractor with appropriate options
if [ "$USE_REPO" = true ] && [ -n "$GITHUB_REPO" ]; then
    echo "Using configuration from GitHub repository: $GITHUB_REPO"
    python docker_extractor.py --config "$CONFIG_FILE" --output "$OUTPUT_DIR" --repo "$GITHUB_REPO" --interval "$CHECK_INTERVAL"
else
    echo "Using local configuration file: $CONFIG_FILE"
    python docker_extractor.py --config "$CONFIG_FILE" --output "$OUTPUT_DIR" --interval "$CHECK_INTERVAL"
fi 