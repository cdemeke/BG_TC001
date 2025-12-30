"""
MQTT publisher for pushing glucose data to AWTRIX3 devices.

This module enables serverless push notifications to AWTRIX3 devices
without requiring a local bridge. AWTRIX3 subscribes to the MQTT broker,
and the cloud service publishes updates.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# MQTT is optional - only import if available
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    mqtt = None


@dataclass
class MQTTConfig:
    """MQTT broker configuration."""
    broker_host: str
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = False
    client_id: str = "dexcom-awtrix-bridge"

    # AWTRIX3 MQTT topics
    # Default topic format: awtrix_<MAC>/custom/<app_name>
    awtrix_prefix: str = "awtrix"
    app_name: str = "glucose"

    @property
    def topic(self) -> str:
        """Get the MQTT topic for publishing."""
        return f"{self.awtrix_prefix}/custom/{self.app_name}"


class MQTTPublisher:
    """
    MQTT publisher for sending glucose data to AWTRIX3 devices.

    AWTRIX3 supports MQTT for receiving custom app data. This publisher
    sends formatted glucose data to the broker, which AWTRIX3 subscribes to.

    Usage:
        publisher = MQTTPublisher(config)
        publisher.connect()
        publisher.publish(awtrix_data)
        publisher.disconnect()
    """

    def __init__(self, config: MQTTConfig):
        """
        Initialize the MQTT publisher.

        Args:
            config: MQTT broker configuration

        Raises:
            ImportError: If paho-mqtt is not installed
        """
        if not MQTT_AVAILABLE:
            raise ImportError(
                "paho-mqtt is required for MQTT support. "
                "Install it with: pip install paho-mqtt"
            )

        self.config = config
        self._client: Optional[mqtt.Client] = None
        self._connected = False

    def connect(self) -> bool:
        """
        Connect to the MQTT broker.

        Returns:
            True if connection successful
        """
        try:
            self._client = mqtt.Client(client_id=self.config.client_id)

            # Set up authentication if provided
            if self.config.username:
                self._client.username_pw_set(
                    self.config.username,
                    self.config.password,
                )

            # Enable TLS if required
            if self.config.use_tls:
                self._client.tls_set()

            # Set up callbacks
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect

            # Connect to broker
            self._client.connect(
                self.config.broker_host,
                self.config.broker_port,
                keepalive=60,
            )

            # Start network loop in background
            self._client.loop_start()

            logger.info(
                f"Connected to MQTT broker at {self.config.broker_host}:{self.config.broker_port}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
            logger.info("Disconnected from MQTT broker")

    def publish(self, data: Dict[str, Any], topic: Optional[str] = None) -> bool:
        """
        Publish data to the MQTT broker.

        Args:
            data: AWTRIX-formatted data dictionary
            topic: Optional custom topic (defaults to config topic)

        Returns:
            True if publish successful
        """
        if not self._client or not self._connected:
            logger.warning("Not connected to MQTT broker")
            return False

        try:
            topic = topic or self.config.topic
            payload = json.dumps(data)

            result = self._client.publish(topic, payload, qos=1)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published to {topic}: {payload[:100]}...")
                return True
            else:
                logger.error(f"Failed to publish: {result.rc}")
                return False

        except Exception as e:
            logger.error(f"Error publishing to MQTT: {e}")
            return False

    def publish_glucose(self, awtrix_response: Dict[str, Any]) -> bool:
        """
        Publish glucose data to AWTRIX3.

        Args:
            awtrix_response: AwtrixResponse as dictionary

        Returns:
            True if publish successful
        """
        return self.publish(awtrix_response)

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when connection is established."""
        if rc == 0:
            self._connected = True
            logger.info("MQTT connection established")
        else:
            logger.error(f"MQTT connection failed with code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when disconnected."""
        self._connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnect: {rc}")


# =============================================================================
# Singleton instance for the application
# =============================================================================

_publisher: Optional[MQTTPublisher] = None


def get_mqtt_publisher(config: Optional[MQTTConfig] = None) -> Optional[MQTTPublisher]:
    """
    Get the MQTT publisher singleton.

    Args:
        config: MQTT configuration (required on first call)

    Returns:
        MQTTPublisher instance or None if MQTT not configured
    """
    global _publisher

    if _publisher is None and config is not None:
        try:
            _publisher = MQTTPublisher(config)
            _publisher.connect()
        except ImportError:
            logger.warning("MQTT not available - paho-mqtt not installed")
            return None

    return _publisher


def reset_mqtt_publisher() -> None:
    """Reset the MQTT publisher (for testing)."""
    global _publisher
    if _publisher:
        _publisher.disconnect()
    _publisher = None
