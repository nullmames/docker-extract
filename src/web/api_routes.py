#!/usr/bin/env python3
from utils.helpers import MetadataManager
import os
import sys
import logging
from flask import Blueprint, jsonify, request
from typing import Dict, List, Set, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our utility modules

logger = logging.getLogger('docker_extractor')

# Configuration
EXTRACTED_DIR = "extracted_binaries"

# Create blueprint
api_bp = Blueprint('api', __name__)

# Initialize metadata manager
metadata_manager = MetadataManager(EXTRACTED_DIR)


@api_bp.route('/metadata')
def get_metadata():
    """Get metadata for all binaries with optional filtering."""
    metadata = metadata_manager.load_global_metadata()

    # Apply filters
    network = request.args.get('network')
    binary_name = request.args.get('binary_name')
    docker_image = request.args.get('docker_image')

    if network:
        metadata = [b for b in metadata if b.get('network') == network]
    if binary_name:
        metadata = [b for b in metadata if b.get('binary_name') == binary_name]
    if docker_image:
        metadata = [b for b in metadata if b.get(
            'docker_image') == docker_image]

    return jsonify(metadata)


@api_bp.route('/networks')
def get_networks():
    """Get a list of all available networks."""
    metadata = metadata_manager.load_global_metadata()
    networks = set()

    for binary in metadata:
        if 'network' in binary:
            networks.add(binary['network'])

    return jsonify(list(networks))
