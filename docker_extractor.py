#!/usr/bin/env python3
import os
import yaml
import docker
import shutil
import tempfile
import subprocess
import time
import hashlib
import sys
import requests
import argparse
import re
from datetime import datetime
from pathlib import Path


class DockerExtractor:
    def __init__(self, config_path, output_dir, config_repo=None):
        self.config_path = config_path
        self.output_dir = output_dir
        self.config_repo = config_repo
        self.last_modified_time = 0
        self.processed_binaries = set()
        self.remote_config_etag = None

        # Try to connect to Docker
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
            print("Successfully connected to Docker")
        except Exception as e:
            print(f"Error connecting to Docker: {e}")
            print("\nPossible issues:")
            print("1. Docker is not running - start the Docker daemon/Desktop app")
            print("2. You don't have permission to access the Docker socket")
            print("3. Docker is not installed correctly")
            sys.exit(1)

    def get_github_raw_url(self, repo_url, file_path='config.yaml'):
        """Convert a GitHub repo URL to a raw content URL for a specific file."""
        # Extract username and repo name from the GitHub URL
        match = re.match(r'https://github.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            print(f"Invalid GitHub repository URL: {repo_url}")
            return None

        username, repo_name = match.groups()
        # Format the raw content URL (using main as the default branch)
        return f"https://raw.githubusercontent.com/{username}/{repo_name}/main/{file_path}"

    def load_config(self):
        """Load configuration from local file or remote repository."""
        # Try to load from remote repository if specified
        if self.config_repo:
            try:
                raw_url = self.get_github_raw_url(self.config_repo)
                if raw_url:
                    print(f"Fetching configuration from: {raw_url}")
                    headers = {}
                    if self.remote_config_etag:
                        headers['If-None-Match'] = self.remote_config_etag

                    response = requests.get(raw_url, headers=headers)

                    # If content hasn't changed (304 Not Modified)
                    if response.status_code == 304:
                        print("Remote configuration unchanged")
                        # Use local file as fallback
                        with open(self.config_path, 'r') as file:
                            return yaml.safe_load(file)

                    # If successful response
                    if response.status_code == 200:
                        # Save the ETag for future requests
                        if 'ETag' in response.headers:
                            self.remote_config_etag = response.headers['ETag']

                        # Update local config file with the remote content
                        with open(self.config_path, 'w') as file:
                            file.write(response.text)

                        print("Updated local configuration from remote repository")
                        return yaml.safe_load(response.text)
                    else:
                        print(
                            f"Failed to fetch remote configuration: {response.status_code}")
                        print("Falling back to local configuration file")
            except Exception as e:
                print(f"Error fetching remote configuration: {e}")
                print("Falling back to local configuration file")

        # Load from local file
        try:
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Error: Config file '{self.config_path}' not found")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML config: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error reading config: {e}")
            sys.exit(1)

    def create_output_dirs(self):
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
                print(f"Created output directory: {self.output_dir}")
            except Exception as e:
                print(f"Error creating output directory: {e}")
                sys.exit(1)

        config = self.load_config()
        for network in config['networks']:
            network_dir = os.path.join(self.output_dir, network['name'])
            if not os.path.exists(network_dir):
                try:
                    os.makedirs(network_dir)
                    print(f"Created network directory: {network_dir}")
                except Exception as e:
                    print(f"Error creating network directory: {e}")
                    sys.exit(1)

    def get_binary_hash(self, binary_path):
        """Compute a hash for the binary file to use for versioning."""
        try:
            hasher = hashlib.sha256()
            with open(binary_path, 'rb') as f:
                buf = f.read(65536)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
            # Using first 12 chars of hash for version folder
            return hasher.hexdigest()[:12]
        except Exception as e:
            print(f"Error hashing binary: {e}")
            return datetime.now().strftime("%Y%m%d%H%M%S")  # Fallback to timestamp

    def binary_exists(self, network_dir, binary_name, docker_image, docker_version):
        """Check if the binary already exists in any version folder."""
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
                                    binary_path = os.path.join(
                                        version_path, binary_name)
                                    if os.path.exists(binary_path):
                                        return True
                    except Exception as e:
                        print(f"Error reading metadata: {e}")
        return False

    def pull_image_with_platform(self, docker_image, docker_version, platform="linux/amd64"):
        """Pull a Docker image with a specific platform."""
        full_image_name = f"{docker_image}:{docker_version}"
        try:
            print(f"Pulling {full_image_name} (platform: {platform})...")

            # Use docker command line to pull with platform specification
            # This is more reliable than the Docker API for platform-specific pulls
            pull_cmd = f"docker pull --platform={platform} {full_image_name}"
            result = subprocess.run(
                pull_cmd, shell=True, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"Error pulling image: {result.stderr}")
                return None

            # Now get the image from the API
            return self.client.images.get(full_image_name)
        except Exception as e:
            print(f"Failed to pull image {full_image_name}: {e}")
            return None

    def extract_binaries(self):
        try:
            config = self.load_config()
            all_metadata = []

            for network in config['networks']:
                network_name = network['name']
                network_dir = os.path.join(self.output_dir, network_name)

                for image_config in network['images']:
                    docker_image = image_config['docker_image']
                    docker_version = image_config['docker_image_version']
                    binary_paths = image_config['binary_paths'].split(',')

                    for binary_path in binary_paths:
                        binary_path = binary_path.strip()
                        binary_name = os.path.basename(binary_path)

                        # Generate a unique key for this binary
                        binary_key = f"{network_name}:{docker_image}:{docker_version}:{binary_path}"

                        # Skip if already processed in this run
                        if binary_key in self.processed_binaries:
                            print(
                                f"Already processed {binary_name} from {docker_image}:{docker_version}")
                            continue

                        # Check if binary already exists
                        if self.binary_exists(network_dir, binary_name, docker_image, docker_version):
                            print(
                                f"Binary {binary_name} from {docker_image}:{docker_version} already exists")
                            self.processed_binaries.add(binary_key)
                            continue

                        # Pull the image with AMD64 platform
                        image = self.pull_image_with_platform(
                            docker_image, docker_version, "linux/amd64")
                        if image is None:
                            continue

                        # Create container with platform specification
                        try:
                            container = self.client.containers.create(
                                f"{docker_image}:{docker_version}",
                                platform="linux/amd64"
                            )
                        except Exception as e:
                            print(
                                f"Failed to create container for {docker_image}:{docker_version}: {e}")
                            continue

                        try:
                            # Create a temporary directory
                            with tempfile.TemporaryDirectory() as temp_dir:
                                # Copy the file from the container
                                cmd = f"docker cp {container.id}:{binary_path} {temp_dir}/{binary_name}"
                                try:
                                    subprocess.run(cmd, shell=True, check=True)
                                    temp_binary_path = f"{temp_dir}/{binary_name}"

                                    # Get binary hash for versioning
                                    binary_hash = self.get_binary_hash(
                                        temp_binary_path)
                                    version_dir = os.path.join(
                                        network_dir, binary_hash)
                                    os.makedirs(version_dir, exist_ok=True)

                                    # Move to final location
                                    target_path = os.path.join(
                                        version_dir, binary_name)
                                    shutil.move(temp_binary_path, target_path)

                                    # Get file size
                                    file_size = os.path.getsize(target_path)

                                    # Store metadata
                                    metadata = {
                                        "binary_name": binary_name,
                                        "docker_image": docker_image,
                                        "docker_version": docker_version,
                                        "size_bytes": file_size,
                                        "network": network_name,
                                        "extraction_date": datetime.now().isoformat(),
                                        "binary_hash": binary_hash,
                                        "original_path": binary_path,
                                        "platform": "linux/amd64"
                                    }

                                    # Save version-specific metadata
                                    version_metadata_path = os.path.join(
                                        version_dir, "metadata.yaml")
                                    with open(version_metadata_path, 'w') as f:
                                        yaml.dump(metadata, f)

                                    all_metadata.append(metadata)
                                    self.processed_binaries.add(binary_key)

                                    print(
                                        f"Extracted {binary_name} ({file_size} bytes) to {version_dir}")
                                except subprocess.CalledProcessError as e:
                                    print(
                                        f"Failed to extract {binary_path}: {e}")
                        finally:
                            # Clean up
                            try:
                                container.remove()
                            except Exception as e:
                                print(f"Error removing container: {e}")

            # Save global metadata
            metadata_path = os.path.join(self.output_dir, "metadata.yaml")

            # If metadata file exists, read it and append new metadata
            existing_metadata = []
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    try:
                        existing_metadata = yaml.safe_load(f) or []
                    except Exception as e:
                        print(f"Error reading existing metadata: {e}")

            # Merge existing and new metadata
            # Remove duplicates based on binary_hash
            combined_metadata = {}
            for item in existing_metadata + all_metadata:
                key = f"{item['network']}:{item['binary_name']}:{item['binary_hash']}"
                combined_metadata[key] = item

            # Save updated metadata
            with open(metadata_path, 'w') as f:
                yaml.dump(list(combined_metadata.values()), f)

            return all_metadata

        except Exception as e:
            print(f"Error during binary extraction: {e}")
            return []

    def config_modified(self):
        """Check if the config file has been modified locally or remotely."""
        try:
            # Check if local file has been modified
            current_mtime = os.path.getmtime(self.config_path)
            local_modified = current_mtime > self.last_modified_time

            # Check if remote config has been modified (if using a repo)
            remote_modified = False
            if self.config_repo:
                raw_url = self.get_github_raw_url(self.config_repo)
                if raw_url:
                    headers = {}
                    if self.remote_config_etag:
                        headers['If-None-Match'] = self.remote_config_etag

                    try:
                        response = requests.head(raw_url, headers=headers)
                        # If status is not 304, the file has changed
                        remote_modified = response.status_code != 304

                        # Update ETag if available
                        if response.status_code == 200 and 'ETag' in response.headers:
                            self.remote_config_etag = response.headers['ETag']
                    except Exception as e:
                        print(f"Error checking remote config: {e}")

            # Update last modified time for local file if either source changed
            if local_modified or remote_modified:
                self.last_modified_time = current_mtime
                return True

            return False
        except Exception as e:
            print(f"Error checking config modification time: {e}")
            return False

    def monitor(self, interval=60):
        """Monitor the config file for changes and extract binaries."""
        print(f"\n{'='*80}")
        print(f"Docker Binary Extractor")
        print(f"{'='*80}")
        print(f"Config file: {self.config_path}")
        if self.config_repo:
            print(f"Config repository: {self.config_repo}")
        print(f"Output directory: {self.output_dir}")
        print(f"Platform: linux/amd64 (forced)")
        print(f"Monitoring interval: {interval} seconds")
        print(f"{'='*80}\n")

        self.create_output_dirs()
        if os.path.exists(self.config_path):
            self.last_modified_time = os.path.getmtime(self.config_path)
        self.extract_binaries()

        print(f"\nMonitoring config file for changes...")
        print(f"Checking every {interval} seconds. Press Ctrl+C to stop.")

        try:
            while True:
                time.sleep(interval)
                if self.config_modified():
                    print(
                        f"\nConfig file changed at {datetime.now().isoformat()}")
                    self.processed_binaries = set()  # Reset processed binaries on config change
                    self.create_output_dirs()
                    self.extract_binaries()
        except KeyboardInterrupt:
            print("\nMonitoring stopped. Goodbye!")


def parse_args():
    parser = argparse.ArgumentParser(
        description='Extract binaries from Docker images based on a configuration file.')
    parser.add_argument('--config', default='config.yaml',
                        help='Path to the configuration file')
    parser.add_argument('--output', default='extracted_binaries',
                        help='Directory to store extracted binaries')
    parser.add_argument(
        '--repo', help='GitHub repository URL for the configuration file')
    parser.add_argument('--interval', type=int, default=60,
                        help='Interval in seconds to check for config changes')
    return parser.parse_args()


if __name__ == "__main__":
    try:
        args = parse_args()
        extractor = DockerExtractor(args.config, args.output, args.repo)
        extractor.monitor(args.interval)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting...")
    except Exception as e:
        print(f"Unhandled error: {e}")
        sys.exit(1)
