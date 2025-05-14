#!/usr/bin/env python3
from utils.helpers import safe_load_yaml, format_download_filename, MetadataManager
import os
import zipfile
import tempfile
import sys
import logging
from flask import Blueprint, render_template, send_file, request, abort, jsonify
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our utility modules

logger = logging.getLogger('docker_extractor')

# Configuration
EXTRACTED_DIR = os.environ.get('OUTPUT_DIR', "extracted_binaries")

# Create blueprint
binary_bp = Blueprint('binary', __name__)

# Helper functions


def find_binary_path(network: str, binary_hash: Optional[str], binary_name: str) -> Optional[str]:
    """Find the binary path based on network, hash and binary name.

    Args:
        network: Network name
        binary_hash: Binary hash (version) or None for latest
        binary_name: Binary name

    Returns:
        Path to the binary or None if not found
    """
    network_dir = os.path.join(EXTRACTED_DIR, network)
    if not os.path.exists(network_dir):
        logger.warning(f"Network directory {network_dir} not found")
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
    # First try to find all version directories containing this binary
    version_dirs = []
    for dir_name in os.listdir(network_dir):
        dir_path = os.path.join(network_dir, dir_name)
        if os.path.isdir(dir_path):
            # Check if the binary exists in this directory
            binary_path = os.path.join(dir_path, binary_name)
            if os.path.exists(binary_path):
                # Check metadata to get extraction date
                metadata_path = os.path.join(dir_path, "metadata.yaml")
                if os.path.exists(metadata_path):
                    try:
                        metadata = safe_load_yaml(metadata_path)
                        if metadata and 'extraction_date' in metadata:
                            version_dirs.append(
                                (metadata['extraction_date'], binary_path))
                            logger.debug(
                                f"Found binary {binary_name} in version {dir_name}")
                    except Exception as e:
                        logger.error(f"Error reading version metadata: {e}")

    if version_dirs:
        # Sort by extraction date (latest first)
        version_dirs.sort(reverse=True)
        logger.info(
            f"Found {len(version_dirs)} versions of {binary_name}, using latest")
        return version_dirs[0][1]

    logger.warning(
        f"No versions found for binary {binary_name} in network {network}")
    return None

# Routes


@binary_bp.route('/binaries/<network>/<binary_name>')
def download_latest_binary(network: str, binary_name: str):
    """Download the latest version of a binary."""
    binary_path = find_binary_path(network, None, binary_name)
    if binary_path:
        try:
            # Use cleaner filename for download
            metadata_path = os.path.join(
                os.path.dirname(binary_path), "metadata.yaml")
            if os.path.exists(metadata_path):
                metadata = safe_load_yaml(metadata_path)
                if metadata and 'docker_version' in metadata:
                    download_name = format_download_filename(
                        binary_name, metadata['docker_version'])
                    logger.info(
                        f"Serving binary {binary_name} with version {metadata['docker_version']}")
                    return send_file(binary_path, as_attachment=True, download_name=download_name)

            # Fallback to original name if metadata not available
            logger.info(f"Serving binary {binary_name} with original name")
            return send_file(binary_path, as_attachment=True)
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            return f"Error serving file: {e}", 500
    logger.warning(f"Binary {binary_name} not found in network {network}")
    return "Binary not found", 404


@binary_bp.route('/binaries/<network>/<binary_hash>/<binary_name>')
def download_versioned_binary(network: str, binary_hash: str, binary_name: str):
    """Download a specific version of a binary based on its hash."""
    binary_path = find_binary_path(network, binary_hash, binary_name)
    if binary_path:
        try:
            # Use cleaner filename for download
            metadata_path = os.path.join(
                os.path.dirname(binary_path), "metadata.yaml")
            if os.path.exists(metadata_path):
                metadata = safe_load_yaml(metadata_path)
                if metadata and 'docker_version' in metadata:
                    download_name = format_download_filename(
                        binary_name, metadata['docker_version'])
                    return send_file(binary_path, as_attachment=True, download_name=download_name)

            # Fallback to original name if metadata not available
            return send_file(binary_path, as_attachment=True)
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            return f"Error serving file: {e}", 500
    return "Binary not found", 404


@binary_bp.route('/download_all_binaries/<network>/<path:docker_image>/<docker_version>')
def download_all_binaries(network: str, docker_image: str, docker_version: str):
    """Download all binaries from a specific Docker image as a zip file."""
    logger.info(
        f"download_all_binaries called with network={network}, docker_image={docker_image}, docker_version={docker_version}")

    # First, let's scan the network directory to find the version hash
    network_dir = os.path.join(EXTRACTED_DIR, network)
    if not os.path.exists(network_dir):
        logger.warning(f"Network directory {network_dir} not found")
        return "Network not found", 404

    # List all version directories in the network directory
    version_dirs = []
    for version_hash in os.listdir(network_dir):
        version_path = os.path.join(network_dir, version_hash)
        if os.path.isdir(version_path):
            # Check if this is the version we're looking for
            metadata_file = os.path.join(version_path, "metadata.yaml")
            if os.path.exists(metadata_file):
                try:
                    metadata = safe_load_yaml(metadata_file)
                    if (metadata and
                        metadata.get('docker_image') == docker_image and
                            metadata.get('docker_version') == docker_version):
                        version_dirs.append(version_path)
                        logger.info(
                            f"Found matching version directory: {version_path}")
                except Exception as e:
                    logger.error(
                        f"Error reading metadata file {metadata_file}: {e}")

    if not version_dirs:
        logger.warning(f"No matching version directories found")
        return "No matching version found", 404

    # Use the first matching version directory
    version_dir = version_dirs[0]

    # Get binary paths from metadata if available
    binary_paths = []
    metadata_path = os.path.join(version_dir, "metadata.yaml")
    if os.path.exists(metadata_path):
        try:
            version_metadata = safe_load_yaml(metadata_path)
            if version_metadata and 'binary_paths' in version_metadata:
                binary_paths_str = version_metadata.get('binary_paths', '')
                if binary_paths_str:
                    binary_paths = [p.strip()
                                    for p in binary_paths_str.split(',')]
                    logger.info(
                        f"Found {len(binary_paths)} binary paths in metadata: {binary_paths}")
        except Exception as e:
            logger.error(f"Error reading version metadata: {e}")

    # If no paths in metadata, get all files in the directory
    if not binary_paths:
        logger.info("No binary paths found in metadata, scanning directory")
        binary_files = [f for f in os.listdir(version_dir)
                        if os.path.isfile(os.path.join(version_dir, f)) and
                        not f.endswith('.metadata.yaml') and
                        f != 'metadata.yaml']
        binary_paths = [
            f"/unknown/{binary_file}" for binary_file in binary_files]
        logger.info(
            f"Found {len(binary_files)} binary files in directory: {binary_files}")

    # Create a temporary file for the zip
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
        temp_path = temp_file.name

    # Create the zip file
    with zipfile.ZipFile(temp_path, 'w') as zipf:
        for path in binary_paths:
            binary_name = os.path.basename(path)
            binary_path = os.path.join(version_dir, binary_name)

            logger.debug(f"Checking binary path: {binary_path}")
            if os.path.exists(binary_path):
                # Remove leading / from path if present
                clean_path = path[1:] if path.startswith('/') else path

                # Add file to zip using its original path
                zipf.write(binary_path, clean_path)
                logger.debug(f"Added {binary_path} to zip as {clean_path}")
            else:
                logger.debug(f"Binary path not found: {binary_path}")

    # Send the zip file
    try:
        # Get the binary name for a cleaner filename
        binary_name = os.path.basename(docker_image).replace('/', '_')

        # Create a clean download filename
        download_name = f"{binary_name}_{docker_version}.zip"

        return send_file(
            temp_path,
            as_attachment=True,
            download_name=download_name
        )
    except Exception as e:
        logger.error(f"Error sending zip file: {e}")
        # Clean up the temp file on error
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return f"Error creating zip file: {e}", 500
