#!/usr/bin/env python3
"""
Local bridge script that fetches glucose data from Cloud Run
and pushes it to an AWTRIX3 device.

This bridge runs on your local network (e.g., Raspberry Pi) and
polls the cloud service, then pushes updates to your AWTRIX device.

Usage:
    python bridge.py --config config.yaml
    python bridge.py --cloud-url https://xxx.run.app --awtrix-ip 192.168.1.87
"""

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import yaml

# =============================================================================
# Constants
# =============================================================================

DEFAULT_POLL_INTERVAL = 60
DEFAULT_HTTP_TIMEOUT = 10
DEFAULT_APP_NAME = "glucose"
MAX_CONSECUTIVE_FAILURES = 5
ERROR_DISPLAY_TEXT = "---"
ERROR_DISPLAY_COLOR = [128, 128, 128]

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# =============================================================================
# Logging Configuration
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class BridgeConfig:
    """
    Bridge configuration with validation.

    Configuration can be loaded from:
    1. YAML config file (highest priority for file-based settings)
    2. Command line arguments
    3. Environment variables
    """
    cloud_run_url: str
    awtrix_ip: str
    app_name: str = DEFAULT_APP_NAME
    poll_interval: int = DEFAULT_POLL_INTERVAL
    timeout: int = DEFAULT_HTTP_TIMEOUT
    run_once: bool = False

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate configuration values."""
        if not self.cloud_run_url:
            raise ValueError("cloud_run_url is required")
        if not self.awtrix_ip:
            raise ValueError("awtrix_ip is required")
        if self.poll_interval < 1:
            raise ValueError("poll_interval must be at least 1 second")
        if self.timeout < 1:
            raise ValueError("timeout must be at least 1 second")

        # Normalize cloud URL
        self.cloud_run_url = self.cloud_run_url.rstrip("/")

    @classmethod
    def from_yaml(cls, config_path: str) -> "BridgeConfig":
        """
        Load configuration from a YAML file.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            BridgeConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required fields are missing
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        return cls(
            cloud_run_url=data.get("cloud_run_url", ""),
            awtrix_ip=data.get("awtrix_ip", ""),
            app_name=data.get("app_name", DEFAULT_APP_NAME),
            poll_interval=data.get("poll_interval", DEFAULT_POLL_INTERVAL),
            timeout=data.get("timeout", DEFAULT_HTTP_TIMEOUT),
        )

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "BridgeConfig":
        """
        Create configuration from command line arguments.

        Args:
            args: Parsed command line arguments

        Returns:
            BridgeConfig instance
        """
        return cls(
            cloud_run_url=args.cloud_url or "",
            awtrix_ip=args.awtrix_ip or "",
            app_name=args.app_name,
            poll_interval=args.interval,
            timeout=args.timeout,
            run_once=args.once,
        )

    @classmethod
    def from_env(cls) -> Optional["BridgeConfig"]:
        """
        Create configuration from environment variables.

        Environment variables:
        - BRIDGE_CLOUD_URL: Cloud Run service URL
        - BRIDGE_AWTRIX_IP: AWTRIX device IP address
        - BRIDGE_APP_NAME: Custom app name (default: glucose)
        - BRIDGE_POLL_INTERVAL: Poll interval in seconds (default: 60)
        - BRIDGE_TIMEOUT: HTTP timeout in seconds (default: 10)

        Returns:
            BridgeConfig instance if env vars are set, None otherwise
        """
        cloud_url = os.environ.get("BRIDGE_CLOUD_URL")
        awtrix_ip = os.environ.get("BRIDGE_AWTRIX_IP")

        if not cloud_url or not awtrix_ip:
            return None

        return cls(
            cloud_run_url=cloud_url,
            awtrix_ip=awtrix_ip,
            app_name=os.environ.get("BRIDGE_APP_NAME", DEFAULT_APP_NAME),
            poll_interval=int(os.environ.get("BRIDGE_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)),
            timeout=int(os.environ.get("BRIDGE_TIMEOUT", DEFAULT_HTTP_TIMEOUT)),
        )


# =============================================================================
# Bridge Implementation
# =============================================================================

@dataclass
class BridgeStatistics:
    """Statistics for bridge operation monitoring."""
    total_fetches: int = 0
    successful_fetches: int = 0
    failed_fetches: int = 0
    total_pushes: int = 0
    successful_pushes: int = 0
    failed_pushes: int = 0
    consecutive_failures: int = 0
    last_success_time: Optional[str] = None
    last_error: Optional[str] = None


class AwtrixBridge:
    """
    Bridge between Cloud Run glucose service and AWTRIX3 device.

    Fetches glucose data from the cloud service and pushes it to
    the AWTRIX device's custom app API.
    """

    def __init__(self, config: BridgeConfig):
        """
        Initialize the bridge.

        Args:
            config: Bridge configuration
        """
        self.config = config
        self.stats = BridgeStatistics()

        # Construct URLs
        self.awtrix_url = f"http://{config.awtrix_ip}/api/custom?name={config.app_name}"
        self.glucose_endpoint = f"{config.cloud_run_url}/glucose"

        logger.info(
            "Bridge initialized",
            extra={
                "cloud_url": config.cloud_run_url,
                "awtrix_ip": config.awtrix_ip,
                "app_name": config.app_name,
                "poll_interval": config.poll_interval,
            }
        )

    def fetch_glucose(self) -> Optional[Dict[str, Any]]:
        """
        Fetch glucose data from Cloud Run service.

        Returns:
            Glucose data dictionary or None if fetch failed
        """
        self.stats.total_fetches += 1

        try:
            response = requests.get(
                self.glucose_endpoint,
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            self.stats.successful_fetches += 1
            return response.json()

        except requests.exceptions.Timeout:
            error_msg = f"Timeout fetching from {self.glucose_endpoint}"
            logger.error(error_msg)
            self.stats.failed_fetches += 1
            self.stats.last_error = error_msg
            return None

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error fetching glucose: {e}"
            logger.error(error_msg)
            self.stats.failed_fetches += 1
            self.stats.last_error = error_msg
            return None

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error fetching glucose: {e.response.status_code}"
            logger.error(error_msg)
            self.stats.failed_fetches += 1
            self.stats.last_error = error_msg
            return None

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch glucose data: {e}"
            logger.error(error_msg)
            self.stats.failed_fetches += 1
            self.stats.last_error = error_msg
            return None

    def push_to_awtrix(self, data: Dict[str, Any]) -> bool:
        """
        Push data to AWTRIX3 device.

        Args:
            data: AWTRIX custom app data dictionary

        Returns:
            True if push succeeded, False otherwise
        """
        self.stats.total_pushes += 1

        try:
            response = requests.post(
                self.awtrix_url,
                json=data,
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            self.stats.successful_pushes += 1

            # Log success with glucose info if available
            text = data.get("text", "")
            if text:
                logger.info(f"Pushed to AWTRIX: {text}")
            else:
                logger.info("Pushed display update to AWTRIX")

            return True

        except requests.exceptions.Timeout:
            error_msg = f"Timeout pushing to AWTRIX at {self.config.awtrix_ip}"
            logger.error(error_msg)
            self.stats.failed_pushes += 1
            self.stats.last_error = error_msg
            return False

        except requests.exceptions.ConnectionError:
            error_msg = f"Cannot connect to AWTRIX at {self.config.awtrix_ip}"
            logger.error(error_msg)
            self.stats.failed_pushes += 1
            self.stats.last_error = error_msg
            return False

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to push to AWTRIX: {e}"
            logger.error(error_msg)
            self.stats.failed_pushes += 1
            self.stats.last_error = error_msg
            return False

    def push_error_display(self, message: str = ERROR_DISPLAY_TEXT) -> bool:
        """
        Push error state to AWTRIX display.

        Args:
            message: Error message to display

        Returns:
            True if push succeeded
        """
        error_data = {
            "text": message,
            "color": ERROR_DISPLAY_COLOR,
            "noScroll": True,
            "center": True,
        }
        return self.push_to_awtrix(error_data)

    def run_once(self) -> bool:
        """
        Execute a single fetch and push cycle.

        Returns:
            True if cycle succeeded, False otherwise
        """
        glucose_data = self.fetch_glucose()

        if glucose_data is None:
            self.push_error_display()
            return False

        return self.push_to_awtrix(glucose_data)

    def run(self) -> None:
        """
        Run continuous polling loop.

        Polls the cloud service and pushes to AWTRIX at the configured interval.
        Logs warnings after consecutive failures.
        """
        logger.info(
            f"Starting bridge: {self.config.cloud_run_url} -> {self.config.awtrix_ip}"
        )
        logger.info(f"Poll interval: {self.config.poll_interval} seconds")

        while True:
            try:
                success = self.run_once()

                if success:
                    self.stats.consecutive_failures = 0
                    from datetime import datetime
                    self.stats.last_success_time = datetime.now().isoformat()
                else:
                    self.stats.consecutive_failures += 1

                if self.stats.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        f"{self.stats.consecutive_failures} consecutive failures. "
                        f"Last error: {self.stats.last_error}"
                    )

                time.sleep(self.config.poll_interval)

            except KeyboardInterrupt:
                logger.info("Shutting down bridge...")
                self._log_final_stats()
                break

            except Exception as e:
                logger.error(f"Unexpected error in bridge loop: {e}", exc_info=True)
                self.stats.consecutive_failures += 1
                self.stats.last_error = str(e)
                time.sleep(self.config.poll_interval)

    def _log_final_stats(self) -> None:
        """Log final statistics on shutdown."""
        logger.info(
            "Bridge statistics",
            extra={
                "total_fetches": self.stats.total_fetches,
                "successful_fetches": self.stats.successful_fetches,
                "failed_fetches": self.stats.failed_fetches,
                "total_pushes": self.stats.total_pushes,
                "successful_pushes": self.stats.successful_pushes,
                "failed_pushes": self.stats.failed_pushes,
            }
        )


# =============================================================================
# CLI
# =============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Bridge between Cloud Run glucose service and AWTRIX3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using config file:
  python bridge.py --config config.yaml

  # Using command line arguments:
  python bridge.py --cloud-url https://my-service.run.app --awtrix-ip 192.168.1.87

  # Run once and exit (useful for testing):
  python bridge.py --config config.yaml --once

Configuration priority (highest to lowest):
  1. Command line arguments
  2. Config file (if --config specified)
  3. Environment variables (BRIDGE_CLOUD_URL, BRIDGE_AWTRIX_IP, etc.)
        """,
    )

    parser.add_argument(
        "--config", "-c",
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--cloud-url",
        help="Cloud Run service URL",
    )
    parser.add_argument(
        "--awtrix-ip",
        help="AWTRIX3 device IP address",
    )
    parser.add_argument(
        "--app-name",
        default=DEFAULT_APP_NAME,
        help=f"AWTRIX custom app name (default: {DEFAULT_APP_NAME})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_POLL_INTERVAL,
        help=f"Poll interval in seconds (default: {DEFAULT_POLL_INTERVAL})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_HTTP_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_HTTP_TIMEOUT})",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (useful for testing)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser


def load_config(args: argparse.Namespace) -> BridgeConfig:
    """
    Load configuration from available sources.

    Priority:
    1. Command line arguments (if cloud-url and awtrix-ip provided)
    2. Config file (if --config specified)
    3. Environment variables

    Args:
        args: Parsed command line arguments

    Returns:
        BridgeConfig instance

    Raises:
        ValueError: If no valid configuration source found
    """
    # Try command line arguments first
    if args.cloud_url and args.awtrix_ip:
        logger.info("Loading configuration from command line arguments")
        return BridgeConfig.from_args(args)

    # Try config file
    if args.config:
        logger.info(f"Loading configuration from {args.config}")
        config = BridgeConfig.from_yaml(args.config)
        config.run_once = args.once
        return config

    # Try environment variables
    config = BridgeConfig.from_env()
    if config:
        logger.info("Loading configuration from environment variables")
        config.run_once = args.once
        return config

    raise ValueError(
        "No valid configuration found. Provide --config file, "
        "--cloud-url and --awtrix-ip arguments, or set BRIDGE_* environment variables."
    )


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = create_parser()
    args = parser.parse_args()

    # Configure verbose logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        config = load_config(args)
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Configuration error: {e}")
        return 1

    bridge = AwtrixBridge(config)

    if config.run_once:
        success = bridge.run_once()
        return 0 if success else 1
    else:
        bridge.run()
        return 0


if __name__ == "__main__":
    sys.exit(main())
