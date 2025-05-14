#!/usr/bin/env python3
"""
Docker Binary Extractor Fix

This script patches the DockerExtractor class to handle the platform parameter issue.
Apply this fix by copying the modified methods to your src/extractor/docker_extractor.py file.
"""


def modified_extract_binaries(self) -> List[Dict]:
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
                        container = self.client.containers.create(
                            f"{docker_image}:{docker_version}",
                            platform="linux/amd64"
                        )
                    else:
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


def modified_monitor(self, interval: int = 60) -> None:
    """Monitor the config file for changes and extract binaries.

    Args:
        interval: Interval in seconds to check for config changes
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Docker Binary Extractor")
    logger.info(f"{'='*80}")
    logger.info(f"Config file: {self.config_manager.config_path}")
    if self.config_manager.config_repo:
        logger.info(
            f"Config repository: {self.config_manager.config_repo}")
    logger.info(f"Output directory: {self.output_dir}")

    # Check if platform support is disabled
    platform_support = os.environ.get(
        'DOCKER_PLATFORM_SUPPORT', 'true').lower() != 'false'
    if platform_support:
        logger.info(f"Platform: linux/amd64 (forced)")
    else:
        logger.info(f"Platform: using default (platform parameter disabled)")

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
