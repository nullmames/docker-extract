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
                data = safe_load_yaml(self.global_metadata_path)
                # Ensure data is always a list
                if isinstance(data, dict):
                    data = [data]
                elif not isinstance(data, list):
                    data = []
                self._metadata_cache = data
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
            # Ensure metadata is a list before saving
            if isinstance(metadata, dict):
                metadata = [metadata]
            elif not isinstance(metadata, list):
                logger.error(f"Invalid metadata type: {type(metadata)}")
                return

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
        # Ensure both inputs are properly formatted as lists
        if existing_metadata is None:
            existing_metadata = []
        elif isinstance(existing_metadata, dict):
            existing_metadata = [existing_metadata]

        if new_metadata is None:
            new_metadata = []
        elif isinstance(new_metadata, dict):
            new_metadata = [new_metadata]

        # Ensure existing_metadata is a list
        if not isinstance(existing_metadata, list):
            logger.warning(
                f"Expected list for existing_metadata, got {type(existing_metadata)}. Converting to empty list.")
            existing_metadata = []

        # Ensure new_metadata is a list
        if not isinstance(new_metadata, list):
            logger.warning(
                f"Expected list for new_metadata, got {type(new_metadata)}. Converting to empty list.")
            new_metadata = []

        combined_metadata = {}

        # Process all metadata entries with extensive error handling
        try:
            # Create a list of all metadata entries
            all_entries = []
            all_entries.extend(
                [entry for entry in existing_metadata if entry and isinstance(entry, dict)])
            all_entries.extend(
                [entry for entry in new_metadata if entry and isinstance(entry, dict)])

            # Process each valid entry
            for item in all_entries:
                if not isinstance(item, dict):
                    logger.warning(
                        f"Skipping non-dict metadata entry: {type(item)}")
                    continue

                # Create a unique key for each entry (with fallbacks for missing fields)
                network = item.get('network', '')
                docker_image = item.get('docker_image', '')
                docker_version = item.get('docker_version', '')
                original_path = item.get('original_path', '')
                binary_name = item.get(
                    'binary_name', os.path.basename(original_path))

                # Use binary_name in the key to ensure uniqueness
                key = f"{network}:{docker_image}:{docker_version}:{binary_name}:{original_path}"
                combined_metadata[key] = item
        except Exception as e:
            logger.error(f"Error during metadata merging: {e}")
            # If anything fails, just return what we have so far
            if not combined_metadata:
                return []

        return list(combined_metadata.values())

    def update_global_metadata(self, new_metadata: List[Dict]) -> None:
        """Update global metadata with new entries.

        Args:
            new_metadata: New metadata entries to add
        """
        try:
            # Extensive type checking and conversion
            if not new_metadata:
                logger.info("No metadata to update (empty list provided)")
                return

            # Ensure new_metadata is a list
            if isinstance(new_metadata, dict):
                new_metadata = [new_metadata]
                logger.info("Converted single dict metadata to list")
            elif not isinstance(new_metadata, list):
                logger.error(
                    f"Cannot process metadata of type: {type(new_metadata)}")
                return

            # Filter out any None or invalid values
            filtered_metadata = []
            for item in new_metadata:
                if item is None:
                    continue
                if not isinstance(item, dict):
                    logger.warning(
                        f"Skipping non-dict metadata entry: {type(item)}")
                    continue

                # Ensure all required keys exist to avoid issues with UI display
                required_keys = ['binary_name', 'docker_image',
                                 'docker_version', 'network', 'original_path']
                missing_keys = [
                    key for key in required_keys if key not in item]

                if missing_keys:
                    logger.warning(
                        f"Metadata entry missing required keys {missing_keys}, filling with default values")
                    for key in missing_keys:
                        if key == 'binary_name':
                            item[key] = item.get('binary_name', os.path.basename(
                                item.get('original_path', 'unknown')))
                        else:
                            item[key] = item.get(key, 'unknown')

                filtered_metadata.append(item)

            if not filtered_metadata:
                logger.info("No valid metadata entries to update")
                return

            # Load existing metadata with robust error handling
            try:
                existing_metadata = self.load_global_metadata(
                    force_reload=True)
                if existing_metadata is None:
                    logger.warning(
                        "Existing metadata was None, using empty list")
                    existing_metadata = []
                elif not isinstance(existing_metadata, list):
                    logger.warning(
                        f"Existing metadata was not a list, converting from {type(existing_metadata)}")
                    if isinstance(existing_metadata, dict):
                        existing_metadata = [existing_metadata]
                    else:
                        existing_metadata = []
            except Exception as e:
                logger.error(f"Error loading existing metadata: {e}")
                existing_metadata = []

            # Merge and save with explicit error handling
            try:
                merged_metadata = self.merge_metadata(
                    existing_metadata, filtered_metadata)
                if merged_metadata:
                    self.save_global_metadata(merged_metadata)
                    logger.info(
                        f"Successfully updated global metadata with {len(filtered_metadata)} new entries. Total entries: {len(merged_metadata)}")
                else:
                    logger.warning("Merged metadata is empty, not saving")
            except Exception as e:
                logger.error(f"Error in merge or save operations: {e}")
        except Exception as e:
            logger.error(f"Unhandled error updating global metadata: {e}")
