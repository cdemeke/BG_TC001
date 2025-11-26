#!/usr/bin/env python3
"""
Local bridge script that fetches glucose data from Cloud Run
and pushes it to an AWTRIX3 device.

Usage:
    python bridge.py --config config.yaml
    python bridge.py --cloud-url https://xxx.run.app --awtrix-ip 192.168.1.87
"""

import argparse
import logging
import sys
import time
from typing import Optional

import requests
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AwtrixBridge:
    """Bridge between Cloud Run glucose service and AWTRIX3."""

    def __init__(
        self,
        cloud_run_url: str,
        awtrix_ip: str,
        app_name: str = "glucose",
        poll_interval: int = 60,
        timeout: int = 10,
    ):
        self.cloud_run_url = cloud_run_url.rstrip("/")
        self.awtrix_ip = awtrix_ip
        self.app_name = app_name
        self.poll_interval = poll_interval
        self.timeout = timeout

        self.awtrix_url = f"http://{awtrix_ip}/api/custom?name={app_name}"
        self.glucose_endpoint = f"{self.cloud_run_url}/glucose"

    def fetch_glucose(self) -> Optional[dict]:
        """Fetch glucose data from Cloud Run service."""
        try:
            response = requests.get(self.glucose_endpoint, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch glucose data: {e}")
            return None

    def push_to_awtrix(self, data: dict) -> bool:
        """Push data to AWTRIX3 device."""
        try:
            response = requests.post(self.awtrix_url, json=data, timeout=self.timeout)
            response.raise_for_status()
            logger.info(f"Pushed to AWTRIX: {data.get('text', 'N/A')}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to push to AWTRIX: {e}")
            return False

    def push_error(self, message: str = "---") -> bool:
        """Push error state to AWTRIX."""
        error_data = {
            "text": message,
            "color": [128, 128, 128],
            "noScroll": True,
            "center": True,
        }
        return self.push_to_awtrix(error_data)

    def run_once(self) -> bool:
        """Execute single poll and push cycle."""
        glucose_data = self.fetch_glucose()

        if glucose_data is None:
            self.push_error("---")
            return False

        return self.push_to_awtrix(glucose_data)

    def run(self):
        """Run continuous polling loop."""
        logger.info(f"Starting bridge: {self.cloud_run_url} -> {self.awtrix_ip}")
        logger.info(f"Poll interval: {self.poll_interval} seconds")

        consecutive_failures = 0
        max_failures = 5

        while True:
            try:
                success = self.run_once()

                if success:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1

                if consecutive_failures >= max_failures:
                    logger.warning(f"{consecutive_failures} consecutive failures")

                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                logger.info("Shutting down bridge...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                consecutive_failures += 1
                time.sleep(self.poll_interval)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Bridge between Cloud Run glucose service and AWTRIX3"
    )
    parser.add_argument("--config", "-c", help="Path to config YAML file")
    parser.add_argument("--cloud-url", help="Cloud Run service URL")
    parser.add_argument("--awtrix-ip", help="AWTRIX3 device IP address")
    parser.add_argument(
        "--app-name", default="glucose", help="AWTRIX custom app name (default: glucose)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Poll interval in seconds (default: 60)",
    )
    parser.add_argument("--once", action="store_true", help="Run once and exit")

    args = parser.parse_args()

    # Load config from file or arguments
    if args.config:
        config = load_config(args.config)
        cloud_url = config.get("cloud_run_url")
        awtrix_ip = config.get("awtrix_ip")
        app_name = config.get("app_name", "glucose")
        poll_interval = config.get("poll_interval", 60)
    else:
        cloud_url = args.cloud_url
        awtrix_ip = args.awtrix_ip
        app_name = args.app_name
        poll_interval = args.interval

    if not cloud_url or not awtrix_ip:
        parser.error("Both cloud-url and awtrix-ip are required")

    bridge = AwtrixBridge(
        cloud_run_url=cloud_url,
        awtrix_ip=awtrix_ip,
        app_name=app_name,
        poll_interval=poll_interval,
    )

    if args.once:
        success = bridge.run_once()
        sys.exit(0 if success else 1)
    else:
        bridge.run()


if __name__ == "__main__":
    main()
