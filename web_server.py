#!/usr/bin/env python3
import os
import yaml
import sys
from flask import Flask, render_template, send_file, jsonify, request, abort, redirect, url_for

# Default port - can be changed if needed
DEFAULT_PORT = 5050

app = Flask(__name__)

EXTRACTED_DIR = "extracted_binaries"
METADATA_PATH = os.path.join(EXTRACTED_DIR, "metadata.yaml")


def load_metadata():
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, 'r') as f:
                return yaml.safe_load(f) or []
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return []
    return []


def find_binary_path(network, binary_hash, binary_name):
    """Find the binary path based on network, hash and binary name."""
    network_dir = os.path.join(EXTRACTED_DIR, network)
    if not os.path.exists(network_dir):
        return None

    # If hash is provided, look in specific version directory
    if binary_hash:
        version_dir = os.path.join(network_dir, binary_hash)
        if os.path.exists(version_dir):
            binary_path = os.path.join(version_dir, binary_name)
            if os.path.exists(binary_path):
                return binary_path
        return None

    # If no hash provided, find the latest version
    version_dirs = []
    for dir_name in os.listdir(network_dir):
        dir_path = os.path.join(network_dir, dir_name)
        if os.path.isdir(dir_path):
            metadata_path = os.path.join(dir_path, "metadata.yaml")
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = yaml.safe_load(f)
                        if metadata and 'extraction_date' in metadata and 'binary_name' in metadata:
                            if metadata['binary_name'] == binary_name:
                                version_dirs.append(
                                    (metadata['extraction_date'], dir_path))
                except Exception as e:
                    print(f"Error reading version metadata: {e}")

    if version_dirs:
        # Sort by extraction date (latest first)
        version_dirs.sort(reverse=True)
        binary_path = os.path.join(version_dirs[0][1], binary_name)
        if os.path.exists(binary_path):
            return binary_path

    return None


@app.route('/')
def index():
    metadata = load_metadata()

    # Organize by network
    networks = {}
    for binary in metadata:
        network_name = binary['network']
        if network_name not in networks:
            networks[network_name] = []
        networks[network_name].append(binary)

    # Sort binaries by extraction date (newest first) within each network
    for network in networks:
        networks[network].sort(key=lambda x: x.get(
            'extraction_date', ''), reverse=True)

    return render_template('index.html', networks=networks)


@app.route('/binaries/<network>/<binary_name>')
def download_latest_binary(network, binary_name):
    """Download the latest version of a binary."""
    binary_path = find_binary_path(network, None, binary_name)
    if binary_path:
        try:
            return send_file(binary_path, as_attachment=True)
        except Exception as e:
            print(f"Error sending file: {e}")
            return f"Error serving file: {e}", 500
    return "Binary not found", 404


@app.route('/binaries/<network>/<binary_hash>/<binary_name>')
def download_versioned_binary(network, binary_hash, binary_name):
    """Download a specific version of a binary based on its hash."""
    binary_path = find_binary_path(network, binary_hash, binary_name)
    if binary_path:
        try:
            return send_file(binary_path, as_attachment=True)
        except Exception as e:
            print(f"Error sending file: {e}")
            return f"Error serving file: {e}", 500
    return "Binary not found", 404


@app.route('/api/metadata')
def get_metadata():
    metadata = load_metadata()

    # Apply filters
    network = request.args.get('network')
    binary_name = request.args.get('binary_name')
    docker_image = request.args.get('docker_image')

    if network:
        metadata = [b for b in metadata if b['network'] == network]
    if binary_name:
        metadata = [b for b in metadata if b['binary_name'] == binary_name]
    if docker_image:
        metadata = [b for b in metadata if b['docker_image'] == docker_image]

    return jsonify(metadata)


@app.route('/api/networks')
def get_networks():
    metadata = load_metadata()
    networks = set()

    for binary in metadata:
        networks.add(binary['network'])

    return jsonify(list(networks))


@app.route('/versions/<network>/<binary_name>')
def show_versions(network, binary_name):
    metadata = load_metadata()
    versions = []

    for binary in metadata:
        if binary['network'] == network and binary['binary_name'] == binary_name:
            versions.append(binary)

    # Sort by extraction date (newest first)
    versions.sort(key=lambda x: x.get('extraction_date', ''), reverse=True)

    return render_template('versions.html', network=network, binary_name=binary_name, versions=versions)


def check_directories():
    """Check if necessary directories exist."""
    if not os.path.exists(EXTRACTED_DIR):
        try:
            os.makedirs(EXTRACTED_DIR)
            print(f"Created directory: {EXTRACTED_DIR}")
        except Exception as e:
            print(f"Error creating directory {EXTRACTED_DIR}: {e}")
            return False

    if not os.path.exists('templates'):
        print(f"Error: 'templates' directory not found. Make sure you are running from the correct directory.")
        return False

    return True


if __name__ == "__main__":
    print(f"\n{'='*80}")
    print(f"Docker Binary Extractor - Web Server")
    print(f"{'='*80}")

    if not check_directories():
        sys.exit(1)

    # Get port from command line if provided
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(
                f"Invalid port number provided. Using default port {DEFAULT_PORT}")

    print(f"Starting web server on http://localhost:{port}")
    print(f"Press Ctrl+C to stop the server")
    print(f"{'='*80}\n")

    try:
        app.run(debug=True, host='0.0.0.0', port=port)
    except OSError as e:
        print(f"\nError starting server: {e}")
        print(f"\nPossible solutions:")
        print(f"1. Try a different port: python web_server.py <port>")
        print(f"2. Find and stop the process using port {port}")
        print(
            f"3. On macOS, disable the 'AirPlay Receiver' service from System Preferences")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nServer stopped by user. Goodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
