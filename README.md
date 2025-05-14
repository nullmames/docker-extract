# Docker Binary Extractor

A tool for extracting binaries from Docker images for analysis and archiving purposes.

## Overview

Docker Binary Extractor is a utility that automatically pulls Docker images, extracts specified binaries, and organizes them for easy access and analysis. It provides both a command-line interface and a web interface for managing and viewing extracted binaries.

## Features

- Extract binaries from Docker images based on configuration
- Organize extracted binaries by network and version
- Monitor configuration for changes and automatically update
- Web interface for browsing and downloading extracted binaries
- API for programmatic access to binary data
- Support for remote configuration via GitHub repositories

## System Requirements

- Docker
- Python 3.10+
- Docker socket access (for extraction functionality)

## Project Structure

```
docker-extract/
├── src/                      # Main application source code
│   ├── extractor/            # Binary extraction functionality
│   ├── web/                  # Web server and API
│   ├── utils/                # Utility functions
│   └── main.py               # Application entry point
├── templates/                # HTML templates for web interface
├── data/                     # Default data directory
├── config.yaml               # Configuration file
├── requirements.txt          # Python dependencies
├── run.sh                    # Script to run the application
├── docker-entrypoint.sh      # Docker container entry point
└── Dockerfile                # Docker image definition
```

## Quick Start

### Local Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd docker-extract
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a configuration file (see Configuration section)

4. Run the application:
   ```
   ./run.sh
   ```

### Docker Deployment

1. Build the Docker image:
   ```
   docker build -t docker-extract .
   ```

2. Run the container:
   ```
   docker run -d \
     -v /var/run/docker.sock:/var/run/docker.sock \
     -v $(pwd)/data:/data \
     -p 5050:5050 \
     -e MODE=both \
     docker-extract
   ```

## Configuration

The application is configured using a YAML file. By default, it looks for `config.yaml` in the current directory.

Example configuration:

```yaml
networks:
  - name: network1
    images:
      - docker_image: ubuntu
        docker_image_version: latest
        binary_paths: /bin/bash,/bin/ls,/usr/bin/python3
  - name: network2
    images:
      - docker_image: nginx
        docker_image_version: latest
        binary_paths: /usr/sbin/nginx,/usr/bin/dumb-init
```

### Remote Configuration

The application supports loading configuration from remote sources:

1. **GitHub Repository**: Provide a GitHub repository URL with the `--repo` option, and the application will fetch the `config.yaml` file from the repository's main branch.

2. **Direct URL**: Set the `CONFIG_PATH` environment variable to a URL, and the application will download the configuration from that URL.

The application will cache the remote configuration locally and use ETags to check for changes, minimizing unnecessary downloads.

## Command Line Options

The application can be run with the following options:

```
Usage: ./run.sh [options]
Options:
  -c, --config FILE     Configuration file (default: config.yaml)
  -o, --output DIR      Output directory (default: extracted_binaries)
  -r, --repo URL        GitHub repository URL for configuration
  -i, --interval SEC    Check interval in seconds (default: 60)
  -p, --port PORT       Web server port (default: 5050)
  -m, --mode MODE       Operation mode: extract, web, or both (default: both)
  -h, --help            Show this help message
```

## Operation Modes

- **extract**: Only run the binary extraction functionality
- **web**: Only run the web server for accessing already extracted binaries
- **both**: Run both extraction and web server (default)

## Web Interface

The web interface is accessible at `http://localhost:5050` (or the configured port) and provides:

- Overview of all extracted binaries organized by network
- Version history for each network
- Binary download functionality

## API Endpoints

The application provides a RESTful API for programmatic access to binary data.

### Metadata API

- **GET /api/metadata**
  - Get metadata for all binaries with optional filtering
  - Query parameters:
    - `network`: Filter by network name
    - `binary_name`: Filter by binary name
    - `docker_image`: Filter by Docker image
  - Response: Array of binary metadata objects

- **GET /api/networks**
  - List all available networks
  - Response: Array of network names

### Binary Download API

- **GET /binaries/{network}/{binary_name}**
  - Download the latest version of a binary from a specific network
  - Response: Binary file content

- **GET /binaries/{network}/{binary_hash}/{binary_name}**
  - Download a specific version of a binary based on its hash
  - Response: Binary file content

- **GET /download_all_binaries/{network}/{docker_image}/{docker_version}**
  - Download all binaries from a specific Docker image as a zip file
  - Response: ZIP file containing all binaries

## Environment Variables

When running in Docker, the following environment variables can be used:

- `CONFIG_PATH`: Path to the configuration file (default: `/app/config.yaml`)
- `OUTPUT_DIR`: Directory to store extracted binaries (default: `/data`)
- `CONFIG_REPO`: GitHub repository URL for remote configuration
- `CHECK_INTERVAL`: Interval in seconds to check for config changes (default: `60`)
- `MODE`: Operation mode: `extract`, `web`, or `both` (default: `extract`)
- `PORT`: Web server port (default: `5050`)
- `PROXY_PATH`: Base path when running behind a reverse proxy
- `DOCKER_PLATFORM_SUPPORT`: Enable/disable Docker platform parameter support (default: `true`)

## Advanced Usage

### Running Behind a Reverse Proxy

To run the application behind a reverse proxy with a path prefix:

```
docker run -d \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/data:/data \
  -p 5050:5050 \
  -e MODE=both \
  -e PROXY_PATH=/extractor \
  docker-extract
```

### Using Remote Configuration

To use a configuration file from a GitHub repository:

```
./run.sh --repo https://github.com/user/repo --interval 300
```

To use a direct URL for configuration:

```
export CONFIG_PATH="https://example.com/path/to/config.yaml"
./run.sh
```

## Troubleshooting

### Docker Socket Permissions

If you encounter permission issues with the Docker socket:

```
chmod 666 /var/run/docker.sock
```

### Platform Support Issues

If you encounter issues with platform-specific Docker images:

```
export DOCKER_PLATFORM_SUPPORT=false
./run.sh
```

## License

[License information]

## Contributing

[Contribution guidelines] 