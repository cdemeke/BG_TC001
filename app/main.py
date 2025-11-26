import logging

from fastapi import Depends, FastAPI, HTTPException

from .awtrix_formatter import format_for_awtrix
from .config import Settings, get_settings
from .dexcom_client import DexcomClient, get_dexcom_client
from .models import AwtrixResponse, GlucoseData, HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dexcom AWTRIX Bridge",
    description="Fetches Dexcom glucose data and formats for AWTRIX3",
    version="1.0.0",
)


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - service info."""
    return {"status": "healthy", "service": "dexcom-awtrix-bridge"}


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "ok"}


@app.get("/glucose", response_model=AwtrixResponse)
async def get_glucose_awtrix(
    dexcom_client: DexcomClient = Depends(get_dexcom_client),
    settings: Settings = Depends(get_settings),
):
    """
    Returns glucose data formatted for AWTRIX3 custom app.

    Rate limited to once per 5 minutes. Returns cached data with a progress
    bar showing countdown to next refresh.

    Response format:
    {
        "text": "120→ +3",
        "color": [0, 255, 0],
        "progress": 60,
        "progressC": [0, 255, 255],
        ...
    }
    """
    try:
        glucose_data, refresh_progress = dexcom_client.get_current_reading()
        if glucose_data is None:
            raise HTTPException(status_code=503, detail="No glucose reading available")
        return format_for_awtrix(glucose_data, settings, refresh_progress)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching glucose: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/glucose/raw", response_model=GlucoseData)
async def get_glucose_raw(
    dexcom_client: DexcomClient = Depends(get_dexcom_client),
):
    """Returns raw glucose data for debugging."""
    try:
        glucose_data, _ = dexcom_client.get_current_reading()
        if glucose_data is None:
            raise HTTPException(status_code=503, detail="No glucose reading available")
        return glucose_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching glucose: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/glucose/status")
async def get_glucose_status(
    dexcom_client: DexcomClient = Depends(get_dexcom_client),
):
    """
    Returns rate limiting status.

    Useful for debugging to see when the next API call will be made.
    """
    seconds_remaining = dexcom_client.get_seconds_until_next_call()
    progress = dexcom_client.get_refresh_progress()

    return {
        "seconds_until_next_refresh": seconds_remaining,
        "refresh_progress_percent": progress,
        "can_refresh_now": seconds_remaining == 0,
    }
