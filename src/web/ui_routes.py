#!/usr/bin/env python3
from utils.helpers import safe_load_yaml
import os
import sys
import logging
from flask import Blueprint, render_template
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our utility modules

logger = logging.getLogger('docker_extractor')

# Configuration
EXTRACTED_DIR = "extracted_binaries"

# Create blueprint
ui_bp = Blueprint('ui', __name__)


@ui_bp.route('/')
def index():
    """Main page showing all extracted binaries organized by network."""
    # First, let's scan the extracted_binaries directory to get all available networks
    networks_data = {}

    if os.path.exists(EXTRACTED_DIR):
        # Get all networks (directories in the extracted_binaries folder)
        for network_name in os.listdir(EXTRACTED_DIR):
            network_path = os.path.join(EXTRACTED_DIR, network_name)
            if os.path.isdir(network_path) and not network_name.startswith('.'):
                networks_data[network_name] = []

                # Get all version directories for this network
                for version_hash in os.listdir(network_path):
                    version_path = os.path.join(network_path, version_hash)
                    if os.path.isdir(version_path):
                        # Read the metadata.yaml file in this version directory
                        metadata_file = os.path.join(
                            version_path, "metadata.yaml")
                        if os.path.exists(metadata_file):
                            try:
                                version_metadata = safe_load_yaml(
                                    metadata_file)

                                # Get all binary files in this version directory
                                binary_files = []
                                binary_paths = []
                                total_size = 0

                                # If binary_paths is in metadata, use it
                                if version_metadata and 'binary_paths' in version_metadata:
                                    binary_paths = [
                                        p.strip() for p in version_metadata['binary_paths'].split(',')]

                                # Get all binary files (non-metadata files)
                                for file_name in os.listdir(version_path):
                                    file_path = os.path.join(
                                        version_path, file_name)
                                    if os.path.isfile(file_path) and not file_name.endswith('.metadata.yaml') and file_name != 'metadata.yaml':
                                        binary_files.append(file_name)
                                        total_size += os.path.getsize(
                                            file_path)

                                # Create a metadata entry for this version
                                if version_metadata:
                                    entry = {
                                        'network': network_name,
                                        'binary_hash': version_hash,
                                        'docker_image': version_metadata.get('docker_image', 'unknown'),
                                        'docker_version': version_metadata.get('docker_version', 'unknown'),
                                        'extraction_date': version_metadata.get('extraction_date', ''),
                                        'binary_files': binary_files,
                                        'binary_paths': binary_paths,
                                        'total_size': total_size
                                    }

                                    networks_data[network_name].append(entry)
                            except Exception as e:
                                logger.error(
                                    f"Error reading metadata file {metadata_file}: {e}")

    # Sort versions by extraction date (newest first) within each network
    for network in networks_data:
        networks_data[network].sort(key=lambda x: x.get(
            'extraction_date', ''), reverse=True)

    return render_template('index.html', networks=networks_data, proxy_path='')


@ui_bp.route('/versions/<network>')
def show_versions(network):
    """Show all versions of binaries for a specific network."""
    metadata_path = os.path.join(EXTRACTED_DIR, "metadata.yaml")
    versions = []

    if os.path.exists(metadata_path):
        try:
            all_metadata = safe_load_yaml(metadata_path)
            versions = [b for b in all_metadata if b.get('network') == network]

            # Sort by extraction date (newest first)
            versions.sort(key=lambda x: x.get(
                'extraction_date', ''), reverse=True)
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")

    return render_template('versions.html', network=network, versions=versions, proxy_path='')
