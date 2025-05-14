#!/usr/bin/env python3
import os
import sys
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Import our blueprints
from .binary_routes import binary_bp
from .api_routes import api_bp
from .ui_routes import ui_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('web_server.log')
    ]
)
logger = logging.getLogger('docker_extractor')

# Default port
DEFAULT_PORT = 5050

# Configuration
EXTRACTED_DIR = os.environ.get('OUTPUT_DIR', "extracted_binaries")
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "templates")


class WebServer:
    """Web server for Docker Binary Extractor."""

    def __init__(self, port=DEFAULT_PORT):
        """Initialize the web server.

        Args:
            port: Port to run the server on
        """
        self.port = port
        self.app = self._create_app()

    def _create_app(self):
        """Create and configure the Flask application.

        Returns:
            Configured Flask application
        """
        app = Flask(__name__, template_folder=TEMPLATES_DIR)

        # Configure the app
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        app.config['PROXY_FIX'] = True

        # Support running behind a path-based proxy (e.g., /extractor)
        proxy_path = os.environ.get('PROXY_PATH', '')

        # Register blueprints with the proxy path prefix
        app.register_blueprint(ui_bp, url_prefix=proxy_path)
        app.register_blueprint(binary_bp, url_prefix=proxy_path)
        app.register_blueprint(api_bp, url_prefix=f"{proxy_path}/api")

        # Apply proxy fix middleware
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

        return app

    def check_directories(self):
        """Check if necessary directories exist.

        Returns:
            True if all directories exist, False otherwise
        """
        if not os.path.exists(EXTRACTED_DIR):
            try:
                os.makedirs(EXTRACTED_DIR)
                logger.info(f"Created directory: {EXTRACTED_DIR}")
            except Exception as e:
                logger.error(f"Error creating directory {EXTRACTED_DIR}: {e}")
                return False

        if not os.path.exists(TEMPLATES_DIR):
            logger.error(
                f"Error: 'templates' directory not found. Make sure you are running from the correct directory.")
            return False

        return True

    def run(self):
        """Run the web server."""
        logger.info(f"\n{'='*80}")
        logger.info(f"Docker Binary Extractor - Web Server")
        logger.info(f"{'='*80}")

        if not self.check_directories():
            sys.exit(1)

        # Check if running behind a proxy
        proxy_path = os.environ.get('PROXY_PATH', '')
        if proxy_path:
            logger.info(f"Running behind a proxy with path: {proxy_path}")

        logger.info(f"Starting web server on http://localhost:{self.port}")
        logger.info(f"Press Ctrl+C to stop the server")
        logger.info(f"{'='*80}\n")

        try:
            self.app.run(debug=True, host='0.0.0.0', port=self.port)
        except OSError as e:
            logger.error(f"\nError starting server: {e}")
            logger.error(f"\nPossible solutions:")
            logger.error(
                f"1. Try a different port: python web_server.py <port>")
            logger.error(
                f"2. Find and stop the process using port {self.port}")
            logger.error(
                f"3. On macOS, disable the 'AirPlay Receiver' service from System Preferences")
            sys.exit(1)
        except KeyboardInterrupt:
            logger.info("\nServer stopped by user. Goodbye!")
        except Exception as e:
            logger.error(f"\nUnexpected error: {e}")
            sys.exit(1)


def parse_args():
    """Parse command line arguments.

    Returns:
        Port number to use for the web server
    """
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.warning(
                f"Invalid port number provided. Using default port {DEFAULT_PORT}")
    return port


if __name__ == "__main__":
    port = parse_args()
    server = WebServer(port)
    server.run()
