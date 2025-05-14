# Docker Binary Extractor

This application extracts binaries from Docker images and provides a web interface to browse and download them.

## Features

- Extract binaries from Docker images based on a YAML configuration
- Organize binaries by network
- **Continuously monitor config file for changes**
- **Version control for binaries (keeps old versions)**
- **Avoids re-downloading existing binaries**
- **Load configuration from GitHub repositories**
- Web interface to browse and download extracted binaries
- API endpoint to access binary metadata
- Detailed metadata including binary name, Docker image, version, size, etc.
- **Clean download filenames** (e.g., "saharad_0.2.0-testnet-beta.zip" instead of "ghcr.io_saharalabsai_sahara_saharad_0.2.0-testnet-beta_binaries.zip")
- **Enhanced error handling** for missing binaries
- **Improved metadata system** that only records successfully extracted binaries

## Using the Docker Container

The easiest way to use Docker Binary Extractor is with the pre-built Docker container:

```bash
# Run the extractor in extract-only mode:
docker run -d \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ./extracted_binaries:/data \
  -e CONFIG_REPO=https://github.com/nullmames/docker-extract \
  ghcr.io/nullmames/docker-extract:latest

# Run the web server only:
docker run -d \
  -p 5050:5050 \
  -v ./extracted_binaries:/data \
  -e MODE=web \
  ghcr.io/nullmames/docker-extract:latest

# Run both extractor and web server:
docker run -d \
  -p 5050:5050 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ./extracted_binaries:/data \
  -e MODE=both \
  -e CONFIG_REPO=https://github.com/nullmames/docker-extract \
  ghcr.io/nullmames/docker-extract:latest
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONFIG_PATH` | Path to configuration file inside container | `/app/config.yaml` |
| `OUTPUT_DIR` | Directory to store extracted binaries | `/data` |
| `CONFIG_REPO` | GitHub repository URL for configuration | (empty) |
| `CHECK_INTERVAL` | Interval to check for config changes (seconds) | `60` |
| `MODE` | Operation mode: `extract`, `web`, or `both` | `extract` |

## Manual Installation

If you prefer to run the application without Docker:

1. Clone this repository
2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

The application uses a YAML configuration file to specify which Docker images to extract binaries from. Edit the `config.yaml` file to customize:

```yaml
networks:
  - name: "ethereum"
    images:
      - docker_image: "ethereum/client-go"
        docker_image_version: "latest"
        binary_paths: "/usr/local/bin/geth"
  - name: "bitcoin"
    images:
      - docker_image: "ruimarinho/bitcoin-core"
        docker_image_version: "latest"
        binary_paths: "/usr/local/bin/bitcoin-cli,/usr/local/bin/bitcoind"
```

- `name`: Network name (used to organize binaries)
- `docker_image`: Docker image name
- `docker_image_version`: Docker image tag/version
- `binary_paths`: Comma-separated list of binary paths to extract

### Using a GitHub Repository for Configuration

You can store your configuration file in a GitHub repository and have the application automatically fetch and use it:

```
./run.sh --repo https://github.com/username/repo
```

This will:
1. Fetch the `config.yaml` file from the specified repository
2. Use that configuration for extracting binaries
3. Periodically check the repository for configuration updates

## Usage (for manual installation)

### Run the Application

Use the provided run script to start the application:

```
./run.sh [options]
```

Available options:
- `-c, --config FILE`: Configuration file path (default: config.yaml)
- `-o, --output DIR`: Output directory (default: extracted_binaries)
- `-r, --repo URL`: GitHub repository URL for configuration
- `-i, --interval SEC`: Check interval in seconds (default: 60)
- `-p, --port PORT`: Web server port (default: 5050)
- `-m, --mode MODE`: Operation mode: extract, web, or both (default: both)
- `-h, --help`: Show help message

### Operation Modes

The application can run in three modes:
1. **Extract mode**: Only extracts binaries from Docker images (`-m extract`)
2. **Web mode**: Only serves the web interface for existing binaries (`-m web`)
3. **Both mode**: Extracts binaries and serves the web interface (`-m both`)

## Versioning System

The application automatically versions binaries based on their content:

- Each binary is stored in a directory named after its hash
- Old versions are preserved when new versions are added
- The web interface shows the latest version by default
- Users can view and download all available versions

## API

The application provides a simple API to access binary metadata:

- `GET /api/metadata`: Get metadata for all binaries
- `GET /api/metadata?network=<network>`: Filter metadata by network
- `GET /api/metadata?binary_name=<n>`: Filter metadata by binary name
- `GET /api/metadata?docker_image=<image>`: Filter metadata by Docker image
- `GET /api/networks`: List all available networks

## Directory Structure

```
.
├── config.yaml             # Configuration file
├── run.sh                  # Main run script
├── src/                    # Source code
│   ├── main.py             # Main entry point
│   ├── extractor/          # Docker extractor module
│   │   └── docker_extractor.py  # Docker extraction logic
│   ├── web/                # Web server module
│   │   ├── server.py       # Web server implementation
│   │   ├── api_routes.py   # API routes
│   │   ├── binary_routes.py # Binary download routes
│   │   └── ui_routes.py    # UI routes
│   └── utils/              # Utility modules
│       ├── helpers.py      # Helper functions
│       └── config_manager.py # Configuration management
├── templates/              # HTML templates
│   ├── index.html          # Main page template
│   └── versions.html       # Binary versions page
├── extracted_binaries/     # Extracted binaries (created on first run)
│   ├── metadata.yaml       # Global binary metadata
│   ├── ethereum/           # Network-specific directories
│   │   ├── <hash1>/        # Version-specific directories
│   │   │   ├── geth        # Binary file
│   │   │   └── metadata.yaml # Version-specific metadata
│   │   └── <hash2>/
│   └── bitcoin/
├── venv/                   # Python virtual environment
└── requirements.txt        # Python dependencies
```

## License

MIT 