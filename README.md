# Docker Binary Extractor

This application extracts binaries from Docker images and provides a web interface to browse and download them.

## Features

- Extract binaries from Docker images based on a YAML configuration
- Organize binaries by network
- **Continuously monitor config file for changes**
- **Version control for binaries (keeps old versions)**
- **Avoids re-downloading existing binaries**
- Web interface to browse and download extracted binaries
- API endpoint to access binary metadata
- Detailed metadata including binary name, Docker image, version, size, etc.

## Requirements

- Python 3.6+
- Docker
- Required Python packages (see `requirements.txt`)

## Installation

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

## Usage

### Extract Binaries

Run the extraction script to pull Docker images and extract the binaries:

```
./run_extractor.sh
# or
python docker_extractor.py
```

This will:
1. Create a directory `extracted_binaries` with network subdirectories
2. Extract the specified binaries from the Docker images
3. Store the binaries in version-specific folders (based on binary hash)
4. Save metadata for each binary
5. **Continuously monitor the config file for changes (every 60 seconds)**
6. **Extract new binaries as they are added to the config file**

### Run the Web Server

Start the web server to browse and download the extracted binaries:

```
./run_server.sh
# or
python web_server.py
```

The web interface will be available at http://localhost:5000.

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
- `GET /api/metadata?binary_name=<name>`: Filter metadata by binary name
- `GET /api/metadata?docker_image=<image>`: Filter metadata by Docker image
- `GET /api/networks`: List all available networks

## Directory Structure

```
.
├── config.yaml             # Configuration file
├── docker_extractor.py     # Script to extract binaries
├── web_server.py           # Web server
├── run_extractor.sh        # Script to run the extractor
├── run_server.sh           # Script to run the web server
├── venv/                   # Python virtual environment
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
└── requirements.txt        # Python dependencies
```

## License

MIT 