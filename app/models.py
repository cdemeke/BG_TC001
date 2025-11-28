from pydantic import BaseModel, Field
from typing import Optional, List


class GlucoseData(BaseModel):
    """Internal glucose data model."""

    value: int = Field(..., description="Glucose value in mg/dL")
    mmol_l: Optional[float] = Field(None, description="Glucose value in mmol/L")
    trend: Optional[int] = Field(None, description="Numeric trend indicator (0-9)")
    trend_direction: Optional[str] = Field(None, description="Trend direction name")
    trend_description: Optional[str] = Field(None, description="Trend description")
    trend_arrow: Optional[str] = Field(None, description="Trend arrow symbol")
    timestamp: Optional[str] = Field(None, description="Reading timestamp ISO format")
    delta: Optional[int] = Field(None, description="Change from previous reading")
    previous_value: Optional[int] = Field(None, description="Previous glucose value")


class AwtrixResponse(BaseModel):
    """AWTRIX3 custom app response format."""

    text: str = Field(..., description="Display text")
    color: List[int] = Field(..., description="RGB color array [R, G, B]")
    icon: Optional[str] = Field(None, description="Icon name or ID")
    duration: Optional[int] = Field(10, description="Display duration in seconds")
    noScroll: Optional[bool] = Field(True, description="Disable text scrolling")
    center: Optional[bool] = Field(True, description="Center the text")
    lifetime: Optional[int] = Field(
        None, description="Seconds before app is removed if not updated"
    )
    background: Optional[List[int]] = Field(None, description="Background RGB color")
    blinkText: Optional[int] = Field(None, description="Text blink interval in ms")
    progress: Optional[int] = Field(
        None, description="Progress bar value 0-100 (shown at bottom of display)"
    )
    progressC: Optional[List[int]] = Field(
        None, description="Progress bar color RGB array"
    )
    progressBC: Optional[List[int]] = Field(
        None, description="Progress bar background color RGB array"
    )
    draw: Optional[List[dict]] = Field(
        None, description="Array of drawing instructions for custom shapes"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "120→ +3",
                "color": [0, 255, 0],
                "icon": "glucose",
                "duration": 10,
                "noScroll": True,
                "center": True,
                "progress": 60,
                "progressC": [0, 255, 255],
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
