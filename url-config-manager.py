#!/usr/bin/env python3
"""
URL Config Manager

This file contains a modified version of the ConfigManager class that adds support for direct URL configurations.
Apply this by replacing the ConfigManager class in src/utils/config_manager.py.
"""


class ConfigManager:
    """Class to manage configuration loading and monitoring."""

    def __init__(self, config_path: str, config_repo: Optional[str] = None):
        """Initialize the configuration manager.

        Args:
            config_path: Path to the configuration file or URL with @ prefix
            config_repo: Optional GitHub repository URL for remote configuration
        """
        # Check if config_path starts with @, indicating a direct URL
        if config_path.startswith('@'):
            self.is_direct_url = True
            self.config_url = config_path[1:]  # Remove the @ prefix
            self.config_path = os.path.join(
                os.getcwd(), "config.yaml")  # Local cache path
            logger.info(f"Using direct URL configuration: {self.config_url}")
        else:
            self.is_direct_url = False
            self.config_path = config_path
            self.config_url = None

        self.config_repo = config_repo
        self.last_modified_time = 0
        self.remote_config_etag = None
        self._config_cache = None

    def get_github_raw_url(self, repo_url: str, file_path: str = 'config.yaml') -> Optional[str]:
        """Convert a GitHub repo URL to a raw content URL for a specific file.

        Args:
            repo_url: GitHub repository URL
            file_path: Path to the file in the repository

        Returns:
            Raw content URL or None if invalid
        """
        match = re.match(r'https://github.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            logger.error(f"Invalid GitHub repository URL: {repo_url}")
            return None

        username, repo_name = match.groups()
        return f"https://raw.githubusercontent.com/{username}/{repo_name}/main/{file_path}"

    def load_config(self, force_reload: bool = False) -> Dict:
        """Load configuration from local file or remote repository/URL with caching.

        Args:
            force_reload: Force reload from disk even if cached

        Returns:
            Configuration dictionary
        """
        # Return cached config if available and not forcing reload
        if not force_reload and self._config_cache is not None:
            return self._config_cache

        # If using direct URL configuration
        if self.is_direct_url:
            try:
                logger.info(
                    f"Fetching configuration from direct URL: {self.config_url}")
                headers = {}
                if self.remote_config_etag:
                    headers['If-None-Match'] = self.remote_config_etag

                response = requests.get(self.config_url, headers=headers)

                # If content hasn't changed (304 Not Modified)
                if response.status_code == 304:
                    logger.info("Direct URL configuration unchanged")
                    if os.path.exists(self.config_path):
                        config = safe_load_yaml(self.config_path)
                        self._config_cache = config
                        return config
                    else:
                        logger.error(
                            "Local cache file doesn't exist, forcing reload")

                # If successful response
                if response.status_code == 200:
                    # Save the ETag for future requests
                    if 'ETag' in response.headers:
                        self.remote_config_etag = response.headers['ETag']

                    # Update local config file with the remote content
                    with open(self.config_path, 'w') as file:
                        file.write(response.text)

                    logger.info("Updated local configuration from direct URL")
                    config = safe_load_yaml(self.config_path)
                    self._config_cache = config
                    return config
                else:
                    logger.warning(
                        f"Failed to fetch direct URL configuration: {response.status_code}")
                    if os.path.exists(self.config_path):
                        logger.info(
                            "Falling back to cached configuration file")
                        config = safe_load_yaml(self.config_path)
                        self._config_cache = config
                        return config
                    else:
                        logger.error("No cached configuration available")
                        return {}
            except Exception as e:
                logger.error(f"Error fetching direct URL configuration: {e}")
                if os.path.exists(self.config_path):
                    logger.info("Falling back to cached configuration file")
                    config = safe_load_yaml(self.config_path)
                    self._config_cache = config
                    return config
                else:
                    logger.error("No cached configuration available")
                    return {}

        # Try to load from remote repository if specified
        if self.config_repo:
            try:
                raw_url = self.get_github_raw_url(self.config_repo)
                if raw_url:
                    logger.info(f"Fetching configuration from repo: {raw_url}")
                    headers = {}
                    if self.remote_config_etag:
                        headers['If-None-Match'] = self.remote_config_etag

                    response = requests.get(raw_url, headers=headers)

                    # If content hasn't changed (304 Not Modified)
                    if response.status_code == 304:
                        logger.info("Remote configuration unchanged")
                        # Use local file as fallback
                        config = safe_load_yaml(self.config_path)
                        self._config_cache = config
                        return config

                    # If successful response
                    if response.status_code == 200:
                        # Save the ETag for future requests
                        if 'ETag' in response.headers:
                            self.remote_config_etag = response.headers['ETag']

                        # Update local config file with the remote content
                        with open(self.config_path, 'w') as file:
                            file.write(response.text)

                        logger.info(
                            "Updated local configuration from remote repository")
                        config = safe_load_yaml(self.config_path)
                        self._config_cache = config
                        return config
                    else:
                        logger.warning(
                            f"Failed to fetch remote configuration: {response.status_code}")
                        logger.info("Falling back to local configuration file")
            except Exception as e:
                logger.error(f"Error fetching remote configuration: {e}")
                logger.info("Falling back to local configuration file")

        # Load from local file
        config = safe_load_yaml(self.config_path)
        self._config_cache = config
        return config

    def config_modified(self) -> bool:
        """Check if the config file has been modified locally or remotely.

        Returns:
            True if the configuration has been modified, False otherwise
        """
        try:
            # Check local file modified time
            if os.path.exists(self.config_path):
                current_mtime = os.path.getmtime(self.config_path)
                local_modified = current_mtime > self.last_modified_time
            else:
                local_modified = False
                current_mtime = 0

            # Check if direct URL config has been modified
            remote_modified = False
            if self.is_direct_url:
                headers = {}
                if self.remote_config_etag:
                    headers['If-None-Match'] = self.remote_config_etag

                try:
                    response = requests.head(self.config_url, headers=headers)
                    # If status is not 304, the file has changed
                    remote_modified = response.status_code != 304

                    # Update ETag if available
                    if response.status_code == 200 and 'ETag' in response.headers:
                        self.remote_config_etag = response.headers['ETag']
                except Exception as e:
                    logger.error(f"Error checking direct URL config: {e}")

            # Check if remote config has been modified (if using a repo)
            elif self.config_repo:
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
                        logger.error(f"Error checking remote config: {e}")

            # Update last modified time for local file if either source changed
            if local_modified or remote_modified:
                self.last_modified_time = current_mtime
                # Force reload of config cache on next load
                self._config_cache = None
                return True

            return False
        except Exception as e:
            logger.error(f"Error checking config modification time: {e}")
            return False
