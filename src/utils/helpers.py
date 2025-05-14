#!/usr/bin/env python3
import os
import yaml
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('docker_extractor.log')
    ]
)
logger = logging.getLogger('docker_extractor')


class FileOperationError(Exception):
    """Exception raised for errors in file operations."""
    pass


def safe_load_yaml(file_path: str) -> Dict:
    """Safely load a YAML file with error handling.

    Args:
        file_path: Path to the YAML file

    Returns:
        Dict containing the parsed YAML data

    Raises:
        FileOperationError: If the file cannot be read or parsed
    """
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise FileOperationError(f"File not found: {file_path}")
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {file_path}: {e}")
        raise FileOperationError(f"Error parsing YAML file: {e}")
    except Exception as e:
        logger.error(f"Unexpected error reading file {file_path}: {e}")
        raise FileOperationError(f"Unexpected error reading file: {e}")


def safe_write_yaml(file_path: str, data: Any) -> None:
    """Safely write data to a YAML file with error handling.

    Args:
        file_path: Path to the YAML file
        data: Data to write to the file

    Raises:
        FileOperationError: If the file cannot be written
    """
    try:
        with open(file_path, 'w') as file:
            yaml.dump(data, file)
    except Exception as e:
        logger.error(f"Error writing to file {file_path}: {e}")
        raise FileOperationError(f"Error writing to file: {e}")


def ensure_directory(directory: str) -> None:
    """Ensure a directory exists, creating it if necessary.

    Args:
        directory: Directory path to create

    Raises:
        FileOperationError: If the directory cannot be created
    """
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {e}")
            raise FileOperationError(f"Error creating directory: {e}")


def get_file_size(file_path: str) -> int:
    """Get the size of a file in bytes.

    Args:
        file_path: Path to the file

    Returns:
        Size of the file in bytes

    Raises:
        FileOperationError: If the file size cannot be determined
    """
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"Error getting file size for {file_path}: {e}")
        raise FileOperationError(f"Error getting file size: {e}")


def format_download_filename(binary_name: str, docker_version: str) -> str:
    """Format a clean download filename for a binary.

    Args:
        binary_name: Name of the binary
        docker_version: Version of the Docker image

    Returns:
        A clean filename for downloading
    """
    # Remove any path components and get just the filename
    filename = os.path.basename(binary_name)

    # Create a clean version string
    clean_version = docker_version.replace(':', '_')

    # Format as filename_version
    return f"{filename}_{clean_version}"


class MetadataManager:
    """Class to manage metadata operations."""

    def __init__(self, base_dir: str):
        """Initialize the metadata manager.

        Args:
            base_dir: Base directory for metadata
        """
        self.base_dir = base_dir
        self.global_metadata_path = os.path.join(base_dir, "metadata.yaml")
        self._metadata_cache = None
        self._last_modified_time = 0

    def load_global_metadata(self, force_reload: bool = False) -> List[Dict]:
        """Load global metadata with caching.

        Args:
            force_reload: Force reload from disk even if cached

        Returns:
            List of metadata entries
        """
        current_mtime = 0
        if os.path.exists(self.global_metadata_path):
            current_mtime = os.path.getmtime(self.global_metadata_path)

        # Return cached data if available and not modified
        if not force_reload and self._metadata_cache is not None and current_mtime <= self._last_modified_time:
            return self._metadata_cache

        # Load from disk
        try:
            if os.path.exists(self.global_metadata_path):
                self._metadata_cache = safe_load_yaml(
                    self.global_metadata_path)
                self._last_modified_time = current_mtime
                return self._metadata_cache
            else:
                self._metadata_cache = []
                return []
        except Exception as e:
            logger.error(f"Error loading global metadata: {e}")
            return []

    def save_global_metadata(self, metadata: List[Dict]) -> None:
        """Save global metadata to disk.

        Args:
            metadata: List of metadata entries to save
        """
        try:
            safe_write_yaml(self.global_metadata_path, metadata)
            self._metadata_cache = metadata
            self._last_modified_time = os.path.getmtime(
                self.global_metadata_path)
        except Exception as e:
            logger.error(f"Error saving global metadata: {e}")

    def merge_metadata(self, existing_metadata: List[Dict], new_metadata: List[Dict]) -> List[Dict]:
        """Merge existing and new metadata, avoiding duplicates.

        Args:
            existing_metadata: Existing metadata entries
            new_metadata: New metadata entries to merge

        Returns:
            Merged metadata list
        """
        combined_metadata = {}

        # Process all metadata entries
        for item in existing_metadata + new_metadata:
            if not item:
                continue

            # Create a unique key for each entry
            key = f"{item.get('network', '')}:{item.get('docker_image', '')}:{item.get('docker_version', '')}:{item.get('original_path', '')}"
            combined_metadata[key] = item

        return list(combined_metadata.values())

    def update_global_metadata(self, new_metadata: List[Dict]) -> None:
        """Update global metadata with new entries.

        Args:
            new_metadata: New metadata entries to add
        """
        existing_metadata = self.load_global_metadata()
        merged_metadata = self.merge_metadata(existing_metadata, new_metadata)
        self.save_global_metadata(merged_metadata)
