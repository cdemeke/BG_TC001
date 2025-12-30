"""
FastAPI application for Dexcom AWTRIX Bridge.

This module provides HTTP endpoints for glucose data formatted
for AWTRIX3 LED matrix displays. Supports both polling mode (AWTRIX
fetches from this service) and push mode (MQTT publishing).
"""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .awtrix_formatter import format_for_awtrix
from .config import Settings, get_settings
from .constants import DEFAULT_LOG_FORMAT
from .dexcom_client import DexcomClient, get_dexcom_client
from .exceptions import (
    DexcomAPIError,
    DexcomAuthError,
    DexcomAwtrixError,
    DexcomNoDataError,
)
from .models import AwtrixResponse, GlucoseData, HealthResponse

# =============================================================================
# Logging Configuration
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format=DEFAULT_LOG_FORMAT,
)
logger = logging.getLogger(__name__)

# MQTT publisher (lazy initialized)
_mqtt_publisher = None


def get_mqtt_publisher_instance(settings: Settings):
    """Get or create the MQTT publisher instance."""
    global _mqtt_publisher

    if not settings.mqtt_enabled:
        return None

    if _mqtt_publisher is None:
        try:
            from .mqtt_publisher import MQTTConfig, MQTTPublisher

            config = MQTTConfig(
                broker_host=settings.mqtt_broker_host,
                broker_port=settings.mqtt_broker_port,
                username=settings.mqtt_username,
                password=settings.mqtt_password,
                use_tls=settings.mqtt_use_tls,
                client_id=settings.mqtt_client_id,
                awtrix_prefix=settings.mqtt_awtrix_prefix,
                app_name=settings.mqtt_app_name,
            )
            _mqtt_publisher = MQTTPublisher(config)
            _mqtt_publisher.connect()
            logger.info("MQTT publisher initialized")
        except ImportError:
            logger.warning("MQTT not available - paho-mqtt not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize MQTT publisher: {e}")
            return None

    return _mqtt_publisher


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    settings = get_settings()
    logger.info("Dexcom AWTRIX Bridge starting up")

    # Initialize MQTT if enabled
    if settings.mqtt_enabled:
        get_mqtt_publisher_instance(settings)

    yield

    # Cleanup MQTT
    global _mqtt_publisher
    if _mqtt_publisher:
        _mqtt_publisher.disconnect()
        _mqtt_publisher = None

    logger.info("Dexcom AWTRIX Bridge shutting down")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Dexcom AWTRIX Bridge",
    description="""
Fetches Dexcom CGM glucose data and formats for AWTRIX3 LED displays.

## Architecture Options

### Option 1: AWTRIX Native Polling (No Local Bridge Required)
Configure your AWTRIX3 to poll the `/glucose` endpoint directly.
See `/docs/remote-setup` for configuration instructions.

### Option 2: MQTT Push (No Local Bridge Required)
Enable MQTT and configure AWTRIX3 to subscribe to the MQTT broker.
The service will push updates automatically.

### Option 3: Local Bridge (Original)
Run the local bridge script to poll this service and push to AWTRIX.
    """,
    version="2.1.0",
    lifespan=lifespan,
)


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(DexcomAwtrixError)
async def dexcom_awtrix_error_handler(
    request: Request,
    exc: DexcomAwtrixError,
) -> JSONResponse:
    """Handle custom application exceptions with structured error responses."""
    logger.error(
        "Application error",
        extra={
            "error_code": exc.error_code.value,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
        }
    )

    status_code = 503 if isinstance(exc, DexcomNoDataError) else 500
    if isinstance(exc, DexcomAuthError):
        status_code = 401

    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict(),
    )


# =============================================================================
# Middleware
# =============================================================================

@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """Add request ID and timing to all requests."""
    request_id = str(uuid.uuid4())[:8]
    start_time = datetime.now()

    # Add request ID to request state
    request.state.request_id = request_id

    response = await call_next(request)

    # Calculate request duration
    duration_ms = (datetime.now() - start_time).total_seconds() * 1000

    # Add response headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

    # Log request completion
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }
    )

    return response


# =============================================================================
# Core Endpoints
# =============================================================================

@app.get("/", response_model=HealthResponse)
async def root():
    """
    Root endpoint - service information.

    Returns service name and status for quick verification.
    """
    return HealthResponse(
        status="healthy",
        service="dexcom-awtrix-bridge",
    )


@app.get("/health")
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Health check endpoint for container orchestration.

    Returns a simple status for liveness probes (Cloud Run, Kubernetes, etc.).
    """
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "mqtt_enabled": settings.mqtt_enabled,
        "mqtt_connected": _mqtt_publisher is not None and _mqtt_publisher._connected if _mqtt_publisher else False,
    }


@app.get("/glucose", response_model=AwtrixResponse)
async def get_glucose_awtrix(
    dexcom_client: DexcomClient = Depends(get_dexcom_client),
    settings: Settings = Depends(get_settings),
):
    """
    Get glucose data formatted for AWTRIX3 custom app.

    This endpoint returns glucose data in a format ready to be pushed
    to an AWTRIX3 device's custom app API.

    **For AWTRIX Native Polling**: Configure AWTRIX to fetch this URL
    every 60 seconds using the HTTP Request App feature.

    **Rate Limiting**: Dexcom API calls are limited to once per 5 minutes.
    Subsequent requests return cached data with a progress bar showing
    countdown to the next refresh.

    **Response Fields**:
    - `text`: Empty (uses draw array for display)
    - `color`: RGB color based on glucose level
    - `draw`: Pixel drawing commands for value, arrow, and delta
    - `progress`: Countdown progress to next refresh (0-100)

    **Example Display**: "149↘-11" (value, trend arrow, delta)
    """
    glucose_data, refresh_progress = dexcom_client.get_current_reading()

    if glucose_data is None:
        raise DexcomNoDataError(
            message="No glucose reading available",
            details="Please ensure your Dexcom sensor is active and connected",
        )

    return format_for_awtrix(glucose_data, settings, refresh_progress)


@app.get("/glucose/raw", response_model=GlucoseData)
async def get_glucose_raw(
    dexcom_client: DexcomClient = Depends(get_dexcom_client),
):
    """
    Get raw glucose data for debugging and custom integrations.

    Returns unformatted glucose data including all available fields
    from the Dexcom API.

    **Response Fields**:
    - `value`: Glucose value in mg/dL
    - `mmol_l`: Glucose value in mmol/L
    - `trend`: Numeric trend indicator (0-9)
    - `trend_direction`: Human-readable trend direction
    - `trend_arrow`: Unicode arrow symbol
    - `delta`: Change from previous reading
    - `timestamp`: ISO 8601 timestamp
    """
    glucose_data, _ = dexcom_client.get_current_reading()

    if glucose_data is None:
        raise DexcomNoDataError(
            message="No glucose reading available",
            details="Please ensure your Dexcom sensor is active and connected",
        )

    return glucose_data


@app.get("/glucose/status")
async def get_glucose_status(
    dexcom_client: DexcomClient = Depends(get_dexcom_client),
    settings: Settings = Depends(get_settings),
):
    """
    Get detailed rate limiting and cache status.

    Useful for debugging and monitoring the bridge's state.

    **Response Fields**:
    - `seconds_until_next_refresh`: Time until next API call allowed
    - `refresh_progress_percent`: Progress bar value (0-100)
    - `can_refresh_now`: Whether a fresh API call will be made
    - `statistics`: API call and cache statistics
    - `mqtt`: MQTT connection status (if enabled)
    """
    seconds_remaining = dexcom_client.get_seconds_until_next_call()
    progress = dexcom_client.get_refresh_progress()
    statistics = dexcom_client.get_statistics()

    # Calculate next refresh time
    next_refresh = None
    if seconds_remaining > 0:
        next_refresh = (datetime.now() + timedelta(seconds=seconds_remaining)).isoformat()

    response = {
        "seconds_until_next_refresh": seconds_remaining,
        "refresh_progress_percent": progress,
        "can_refresh_now": seconds_remaining == 0,
        "next_refresh_at": next_refresh,
        "statistics": statistics,
    }

    # Add MQTT status if enabled
    if settings.mqtt_enabled:
        response["mqtt"] = {
            "enabled": True,
            "connected": _mqtt_publisher is not None and _mqtt_publisher._connected if _mqtt_publisher else False,
            "broker": settings.mqtt_broker_host,
            "topic": f"{settings.mqtt_awtrix_prefix}/custom/{settings.mqtt_app_name}",
        }

    return response


@app.get("/glucose/statistics")
async def get_statistics(
    dexcom_client: DexcomClient = Depends(get_dexcom_client),
):
    """
    Get API usage statistics.

    Provides insights into API performance and cache effectiveness.

    **Response Fields**:
    - `total_api_calls`: Number of actual Dexcom API calls made
    - `cache_hits`: Number of requests served from cache
    - `api_errors`: Number of API errors encountered
    - `cache_hit_rate`: Percentage of requests served from cache
    """
    return dexcom_client.get_statistics()


# =============================================================================
# MQTT Endpoints
# =============================================================================

@app.post("/mqtt/publish")
async def mqtt_publish(
    dexcom_client: DexcomClient = Depends(get_dexcom_client),
    settings: Settings = Depends(get_settings),
):
    """
    Publish glucose data to MQTT broker.

    This endpoint fetches the latest glucose data and publishes it
    to the configured MQTT broker. Can be called by Cloud Scheduler
    or other cron services for regular updates.

    **Use Case**: Set up Cloud Scheduler to call this endpoint every
    minute to push updates to your AWTRIX3 without a local bridge.

    **Requirements**:
    - MQTT must be enabled via MQTT_ENABLED=true
    - MQTT broker must be configured

    **Returns**:
    - `published`: Whether the publish was successful
    - `topic`: The MQTT topic used
    - `glucose_value`: The glucose value that was published
    """
    if not settings.mqtt_enabled:
        raise HTTPException(
            status_code=400,
            detail="MQTT is not enabled. Set MQTT_ENABLED=true in environment.",
        )

    publisher = get_mqtt_publisher_instance(settings)
    if publisher is None:
        raise HTTPException(
            status_code=503,
            detail="MQTT publisher not available. Check paho-mqtt installation.",
        )

    # Get glucose data
    glucose_data, refresh_progress = dexcom_client.get_current_reading()

    if glucose_data is None:
        raise DexcomNoDataError(
            message="No glucose reading available",
            details="Please ensure your Dexcom sensor is active and connected",
        )

    # Format for AWTRIX
    awtrix_data = format_for_awtrix(glucose_data, settings, refresh_progress)

    # Publish to MQTT
    success = publisher.publish_glucose(awtrix_data.model_dump(exclude_none=True))

    if not success:
        raise HTTPException(
            status_code=503,
            detail="Failed to publish to MQTT broker",
        )

    return {
        "published": True,
        "topic": f"{settings.mqtt_awtrix_prefix}/custom/{settings.mqtt_app_name}",
        "glucose_value": glucose_data.value,
        "delta": glucose_data.delta,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/mqtt/status")
async def mqtt_status(settings: Settings = Depends(get_settings)):
    """
    Get MQTT connection status.

    **Response Fields**:
    - `enabled`: Whether MQTT is enabled
    - `connected`: Whether currently connected to broker
    - `broker`: MQTT broker hostname
    - `topic`: MQTT topic for publishing
    """
    if not settings.mqtt_enabled:
        return {
            "enabled": False,
            "message": "MQTT is not enabled. Set MQTT_ENABLED=true to enable.",
        }

    publisher = get_mqtt_publisher_instance(settings)

    return {
        "enabled": True,
        "connected": publisher is not None and publisher._connected if publisher else False,
        "broker": f"{settings.mqtt_broker_host}:{settings.mqtt_broker_port}",
        "topic": f"{settings.mqtt_awtrix_prefix}/custom/{settings.mqtt_app_name}",
        "use_tls": settings.mqtt_use_tls,
    }


# =============================================================================
# Setup Guide Endpoint
# =============================================================================

@app.get("/setup/remote")
async def get_remote_setup_guide():
    """
    Get instructions for remote-only setup (no local bridge).

    Returns step-by-step instructions for configuring AWTRIX3
    to poll this service directly or use MQTT.
    """
    return {
        "title": "Remote-Only Setup Guide",
        "description": "Configure AWTRIX3 without a local bridge",
        "options": [
            {
                "name": "Option 1: AWTRIX Native HTTP Polling",
                "description": "AWTRIX3 polls your Cloud Run service directly",
                "difficulty": "Easy",
                "steps": [
                    "1. Deploy this service to Cloud Run (see README)",
                    "2. Get your Cloud Run URL (e.g., https://dexcom-awtrix-xxx.run.app)",
                    "3. Open AWTRIX3 web interface (http://YOUR_AWTRIX_IP)",
                    "4. Go to Apps → HTTP Request App",
                    "5. Configure: URL = YOUR_CLOUD_RUN_URL/glucose",
                    "6. Set polling interval to 60 seconds",
                    "7. Enable 'Parse as AWTRIX App'",
                ],
                "pros": ["Simple setup", "No additional services needed"],
                "cons": ["Requires AWTRIX3 firmware 0.90+", "One-way communication"],
            },
            {
                "name": "Option 2: MQTT Push",
                "description": "Cloud service pushes updates via MQTT broker",
                "difficulty": "Medium",
                "steps": [
                    "1. Set up an MQTT broker (HiveMQ Cloud, CloudMQTT, or self-hosted)",
                    "2. Configure AWTRIX3 MQTT settings to connect to broker",
                    "3. Set environment variables: MQTT_ENABLED=true, MQTT_BROKER_HOST=...",
                    "4. Set up Cloud Scheduler to call POST /mqtt/publish every minute",
                    "5. AWTRIX3 will receive updates automatically",
                ],
                "environment_variables": {
                    "MQTT_ENABLED": "true",
                    "MQTT_BROKER_HOST": "broker.hivemq.com",
                    "MQTT_BROKER_PORT": "1883",
                    "MQTT_USERNAME": "(optional)",
                    "MQTT_PASSWORD": "(optional)",
                    "MQTT_USE_TLS": "false",
                    "MQTT_AWTRIX_PREFIX": "awtrix",
                    "MQTT_APP_NAME": "glucose",
                },
                "pros": ["Real-time updates", "Bi-directional communication possible"],
                "cons": ["Requires MQTT broker", "More complex setup"],
            },
        ],
    }
