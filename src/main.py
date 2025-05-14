#!/usr/bin/env python3
from web.server import WebServer
from extractor.docker_extractor import DockerExtractor
import os
import sys
import argparse
import logging
import threading
from typing import Optional

# Add the src directory to the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('docker_extract.log')
    ]
)
logger = logging.getLogger('docker_extractor')

# Default values
DEFAULT_CONFIG_PATH = "config.yaml"
DEFAULT_OUTPUT_DIR = "extracted_binaries"
DEFAULT_CHECK_INTERVAL = 60
DEFAULT_PORT = 5050


class DockerExtractApp:
    """Main application for Docker Binary Extractor."""

    def __init__(self,
                 config_path: str = DEFAULT_CONFIG_PATH,
                 output_dir: str = DEFAULT_OUTPUT_DIR,
                 config_repo: Optional[str] = None,
                 check_interval: int = DEFAULT_CHECK_INTERVAL,
                 port: int = DEFAULT_PORT,
                 mode: str = "both"):
        """Initialize the application.

        Args:
            config_path: Path to the configuration file
            output_dir: Directory to store extracted binaries
            config_repo: Optional GitHub repository URL for remote configuration
            check_interval: Interval in seconds to check for config changes
            port: Port to run the web server on
            mode: Operation mode: 'extract', 'web', or 'both'
        """
        self.config_path = config_path
        self.output_dir = output_dir
        self.config_repo = config_repo
        self.check_interval = check_interval
        self.port = port
        self.mode = mode

        # Initialize components based on mode
        self.extractor = None
        self.web_server = None

        if mode in ['extract', 'both']:
            self.extractor = DockerExtractor(
                config_path, output_dir, config_repo)

        if mode in ['web', 'both']:
            self.web_server = WebServer(port)

    def run_extractor(self):
        """Run the extractor component."""
        try:
            self.extractor.monitor(self.check_interval)
        except Exception as e:
            logger.error(f"Error in extractor thread: {e}")

    def run(self):
        """Run the application in the specified mode."""
        if self.mode == 'extract':
            logger.info(f"Running in extract-only mode")
            self.extractor.monitor(self.check_interval)
        elif self.mode == 'web':
            logger.info(f"Running in web-only mode")
            self.web_server.run()
        elif self.mode == 'both':
            logger.info(f"Running in both extract and web mode")
            # Use threading to run both components simultaneously
            extractor_thread = threading.Thread(target=self.run_extractor)
            # Allow the program to exit even if thread is running
            extractor_thread.daemon = True
            extractor_thread.start()

            # Run web server in the main thread
            logger.info(f"Starting web server on port {self.port}")
            self.web_server.run()
        else:
            logger.error(f"Invalid mode: {self.mode}")
            sys.exit(1)


def parse_args():
    """Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Docker Binary Extractor - Download and extract binaries from Docker images')

    parser.add_argument('--config', default=DEFAULT_CONFIG_PATH,
                        help=f'Path to the configuration file (default: {DEFAULT_CONFIG_PATH})')
    parser.add_argument('--output', default=DEFAULT_OUTPUT_DIR,
                        help=f'Directory to store extracted binaries (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--repo',
                        help='GitHub repository URL for the configuration file')
    parser.add_argument('--interval', type=int, default=DEFAULT_CHECK_INTERVAL,
                        help=f'Interval in seconds to check for config changes (default: {DEFAULT_CHECK_INTERVAL})')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                        help=f'Port to run the web server on (default: {DEFAULT_PORT})')
    parser.add_argument('--mode', choices=['extract', 'web', 'both'], default='both',
                        help='Operation mode: extract, web, or both (default: both)')

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    app = DockerExtractApp(
        config_path=args.config,
        output_dir=args.output,
        config_repo=args.repo,
        check_interval=args.interval,
        port=args.port,
        mode=args.mode
    )

    app.run()
