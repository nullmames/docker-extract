#!/usr/bin/env python3
from utils.config_manager import ConfigManager
from utils.helpers import ensure_directory, get_file_size, safe_write_yaml, MetadataManager, logger
import os
import docker
import shutil
import tempfile
import subprocess
import hashlib
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our utility modules


class DockerExtractor:
    """Class for extracting binaries from Docker images."""

    def __init__(self, config_path: str, output_dir: str, config_repo: Optional[str] = None):
        """Initialize the Docker extractor.

        Args:
            config_path: Path to the configuration file
            output_dir: Directory to store extracted binaries
            config_repo: Optional GitHub repository URL for remote configuration
        """
        self.config_manager = ConfigManager(config_path, config_repo)
        self.output_dir = output_dir
        self.processed_binaries = set()
        self.metadata_manager = MetadataManager(output_dir)

        # Initialize Docker client
        self._init_docker_client()

    def _init_docker_client(self) -> None:
        """Initialize the Docker client with error handling."""
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
            logger.info("Successfully connected to Docker")
        except Exception as e:
            logger.error(f"Error connecting to Docker: {e}")
            logger.error("Possible issues:")
            logger.error(
                "1. Docker is not running - start the Docker daemon/Desktop app")
            logger.error(
                "2. You don't have permission to access the Docker socket")
            logger.error("3. Docker is not installed correctly")
            sys.exit(1)

    def create_output_dirs(self) -> None:
        """Create output directories based on configuration."""
        # Create main output directory
        ensure_directory(self.output_dir)

        # Create network directories
        config = self.config_manager.load_config()
        for network in config.get('networks', []):
            network_dir = os.path.join(self.output_dir, network['name'])
            ensure_directory(network_dir)

    def generate_image_hash(self, docker_image: str, docker_version: str) -> str:
        """Generate a consistent hash for a Docker image and version.

        Args:
            docker_image: Docker image name
            docker_version: Docker image version

        Returns:
            Hash string for the image
        """
        image_str = f"{docker_image}:{docker_version}"
        return hashlib.sha256(image_str.encode()).hexdigest()[:12]

    def pull_image_with_platform(self, docker_image: str, docker_version: str, platform: str = "linux/amd64") -> Optional[docker.models.images.Image]:
        """Pull a Docker image with a specific platform.

        Args:
            docker_image: Docker image name
            docker_version: Docker image version
            platform: Platform to pull for (default: linux/amd64)

        Returns:
            Docker image object or None if pull failed
        """
        full_image_name = f"{docker_image}:{docker_version}"
        try:
            logger.info(f"Pulling {full_image_name} (platform: {platform})...")

            # Use docker command line to pull with platform specification
            # This is more reliable than the Docker API for platform-specific pulls
            pull_cmd = f"docker pull --platform={platform} {full_image_name}"
            result = subprocess.run(
                pull_cmd, shell=True, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"Error pulling image: {result.stderr}")
                return None

            # Now get the image from the API
            return self.client.images.get(full_image_name)
        except Exception as e:
            logger.error(f"Failed to pull image {full_image_name}: {e}")
            return None

    def binary_exists(self, network_dir: str, binary_name: str, docker_image: str, docker_version: str, binary_path: str) -> bool:
        """Check if a binary already exists in any version folder.

        Args:
            network_dir: Network directory path
            binary_name: Name of the binary
            docker_image: Docker image name
            docker_version: Docker image version
            binary_path: Original path of the binary in the container

        Returns:
            True if the binary exists, False otherwise
        """
        if not os.path.exists(network_dir):
            return False

        for version_dir in os.listdir(network_dir):
            version_path = os.path.join(network_dir, version_dir)
            if os.path.isdir(version_path):
                metadata_path = os.path.join(version_path, "metadata.yaml")
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = yaml.safe_load(f)
                            if metadata and "docker_image" in metadata and "docker_version" in metadata:
                                if metadata["docker_image"] == docker_image and metadata["docker_version"] == docker_version:
                                    if "original_path" in metadata and metadata["original_path"] == binary_path:
                                        binary_path = os.path.join(
                                            version_path, binary_name)
                                        if os.path.exists(binary_path):
                                            return True
                    except Exception as e:
                        logger.error(f"Error reading metadata: {e}")
        return False

    def extract_binary(self, container_id: str, binary_path: str, temp_dir: str) -> Tuple[bool, str, Optional[int]]:
        """Extract a binary from a container to a temporary directory.

        Args:
            container_id: Docker container ID
            binary_path: Path to the binary in the container
            temp_dir: Temporary directory to extract to

        Returns:
            Tuple of (success, binary_name, file_size)
        """
        binary_name = os.path.basename(binary_path)
        temp_binary_path = os.path.join(temp_dir, binary_name)

        # Copy the file from the container
        cmd = f"docker cp {container_id}:{binary_path} {temp_binary_path}"
        try:
            subprocess.run(cmd, shell=True, check=True)

            # Verify the file was copied correctly
            if not os.path.exists(temp_binary_path):
                logger.warning(f"Failed to copy {binary_name} from container")
                return False, binary_name, None

            # Get file size
            file_size = get_file_size(temp_binary_path)
            return True, binary_name, file_size

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract {binary_path}: {e}")
            return False, binary_name, None
        except Exception as e:
            logger.error(f"Error processing {binary_path}: {e}")
            return False, binary_name, None

    def process_binary(self,
                       network_name: str,
                       docker_image: str,
                       docker_version: str,
                       binary_path: str,
                       container_id: str,
                       version_dir: str,
                       processed_binaries: Set[str]) -> Tuple[bool, Optional[Dict]]:
        """Process a single binary from a container.

        Args:
            network_name: Name of the network
            docker_image: Docker image name
            docker_version: Docker image version
            binary_path: Path to the binary in the container
            container_id: Docker container ID
            version_dir: Directory to store the binary version
            processed_binaries: Set of already processed binaries

        Returns:
            Tuple of (success, metadata)
        """
        binary_path = binary_path.strip()
        binary_name = os.path.basename(binary_path)

        # Generate a unique key for this binary
        binary_key = f"{network_name}:{docker_image}:{docker_version}:{binary_path}"

        # Skip if already processed in this run
        if binary_key in processed_binaries:
            logger.info(
                f"Already processed {binary_name} from {docker_image}:{docker_version}")
            return True, None

        # Skip if binary already exists in any version folder
        network_dir = os.path.dirname(version_dir)
        if self.binary_exists(network_dir, binary_name, docker_image, docker_version, binary_path):
            logger.info(
                f"Binary {binary_name} from {docker_image}:{docker_version} already exists")
            processed_binaries.add(binary_key)
            return True, None

        # Extract the binary to a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            success, binary_name, file_size = self.extract_binary(
                container_id, binary_path, temp_dir)

            if not success:
                return False, None

            # Move to final location
            temp_binary_path = os.path.join(temp_dir, binary_name)
            target_path = os.path.join(version_dir, binary_name)
            shutil.move(temp_binary_path, target_path)

            # Generate metadata
            image_hash = self.generate_image_hash(docker_image, docker_version)
            metadata = {
                "binary_name": binary_name,
                "docker_image": docker_image,
                "docker_version": docker_version,
                "size_bytes": file_size,
                "network": network_name,
                "extraction_date": datetime.now().isoformat(),
                "binary_hash": image_hash,
                "original_path": binary_path,
                "platform": "linux/amd64"
            }

            # Save binary-specific metadata file
            binary_metadata_path = os.path.join(
                version_dir, f"{binary_name}.metadata.yaml")
            safe_write_yaml(binary_metadata_path, metadata)

            processed_binaries.add(binary_key)
            logger.info(
                f"Extracted {binary_name} ({file_size} bytes) to {version_dir}")

            return True, metadata

    def extract_binaries(self) -> List[Dict]:
        """Extract binaries from Docker images based on configuration.

        Returns:
            List of metadata for extracted binaries
        """
        try:
            config = self.config_manager.load_config()
            all_metadata = []

            # Check if platform support is disabled via environment variable
            platform_support = os.environ.get(
                'DOCKER_PLATFORM_SUPPORT', 'true').lower() != 'false'

            if not platform_support:
                logger.info(
                    "Docker platform parameter support is disabled via environment variable")

            for network in config.get('networks', []):
                network_name = network['name']
                network_dir = os.path.join(self.output_dir, network_name)

                for image_config in network.get('images', []):
                    docker_image = image_config['docker_image']
                    docker_version = image_config['docker_image_version']
                    binary_paths = image_config['binary_paths'].split(',')

                    # Use a consistent hash for the version folder
                    image_hash = self.generate_image_hash(
                        docker_image, docker_version)
                    version_dir = os.path.join(network_dir, image_hash)
                    ensure_directory(version_dir)

                    # Create a new container for this image only once
                    container = None
                    try:
                        # Pull the image with AMD64 platform
                        image = self.pull_image_with_platform(
                            docker_image, docker_version)
                        if image is None:
                            continue

                        # Create container with or without platform specification based on support
                        if platform_support:
                            try:
                                container = self.client.containers.create(
                                    f"{docker_image}:{docker_version}",
                                    platform="linux/amd64"
                                )
                            except TypeError as e:
                                # If platform parameter is not supported, try without it
                                logger.warning(
                                    f"Platform parameter not supported by Docker SDK: {e}")
                                container = self.client.containers.create(
                                    f"{docker_image}:{docker_version}"
                                )
                        else:
                            # Create container without platform specification
                            container = self.client.containers.create(
                                f"{docker_image}:{docker_version}"
                            )

                        # Process each binary path
                        successful_paths = []
                        successful_metadata = []

                        for binary_path in binary_paths:
                            success, metadata = self.process_binary(
                                network_name,
                                docker_image,
                                docker_version,
                                binary_path,
                                container.id,
                                version_dir,
                                self.processed_binaries
                            )

                            if success:
                                successful_paths.append(binary_path)
                                if metadata:
                                    successful_metadata.append(metadata)
                                    all_metadata.append(metadata)

                        # Save version-level metadata with only successful binary paths
                        if successful_paths:
                            all_paths = ",".join(successful_paths)
                            version_metadata = {
                                "docker_image": docker_image,
                                "docker_version": docker_version,
                                "network": network_name,
                                "extraction_date": datetime.now().isoformat(),
                                "binary_paths": all_paths,
                                "binary_hash": image_hash,
                                "platform": "linux/amd64"
                            }

                            version_metadata_path = os.path.join(
                                version_dir, "metadata.yaml")
                            safe_write_yaml(
                                version_metadata_path, version_metadata)

                    except Exception as e:
                        logger.error(
                            f"Error processing image {docker_image}:{docker_version}: {e}")
                    finally:
                        # Clean up
                        if container:
                            try:
                                container.remove()
                            except Exception as e:
                                logger.error(f"Error removing container: {e}")

            # Update global metadata
            self.metadata_manager.update_global_metadata(all_metadata)
            return all_metadata

        except Exception as e:
            logger.error(f"Error during binary extraction: {e}")
            return []

    def monitor(self, interval: int = 60) -> None:
        """Monitor the config file for changes and extract binaries.

        Args:
            interval: Interval in seconds to check for config changes
        """
        # Check if platform support is disabled via environment variable
        platform_support = os.environ.get(
            'DOCKER_PLATFORM_SUPPORT', 'true').lower() != 'false'

        logger.info(f"\n{'='*80}")
        logger.info(f"Docker Binary Extractor")
        logger.info(f"{'='*80}")
        logger.info(f"Config file: {self.config_manager.config_path}")
        if self.config_manager.config_repo:
            logger.info(
                f"Config repository: {self.config_manager.config_repo}")
        logger.info(f"Output directory: {self.output_dir}")

        if platform_support:
            logger.info(f"Platform: linux/amd64 (forced)")
        else:
            logger.info(f"Platform: default (platform parameter disabled)")

        logger.info(f"Monitoring interval: {interval} seconds")
        logger.info(f"{'='*80}\n")

        self.create_output_dirs()
        if os.path.exists(self.config_manager.config_path):
            self.config_manager.last_modified_time = os.path.getmtime(
                self.config_manager.config_path)
        self.extract_binaries()

        logger.info(f"\nMonitoring config file for changes...")
        logger.info(
            f"Checking every {interval} seconds. Press Ctrl+C to stop.")

        try:
            while True:
                time.sleep(interval)
                if self.config_manager.config_modified():
                    logger.info(
                        f"\nConfig file changed at {datetime.now().isoformat()}")
                    self.processed_binaries = set()  # Reset processed binaries on config change
                    self.create_output_dirs()
                    self.extract_binaries()
        except KeyboardInterrupt:
            logger.info("\nMonitoring stopped. Goodbye!")
