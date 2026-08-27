"""Provider-neutral active-fire data models."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from .const import (
    ATTR_ACQUIRED,
    ATTR_CONFIDENCE,
    ATTR_DISTANCE_KM,
    ATTR_FRP_MW,
    ATTR_LATITUDE,
    ATTR_LOCATION_DESCRIPTION,
    ATTR_LONGITUDE,
    ATTR_NEAREST_SETTLEMENT,
    ATTR_PEAK_FRP_MW,
    ATTR_PIXEL_COUNT,
    ATTR_PLACE_ATTRIBUTION,
    ATTR_PLACE_NAME,
    ATTR_TRACK_ID,
)


class ProviderStatus(StrEnum):
    """Availability state reported by an active-fire provider."""

    AVAILABLE = "available"
    DELAYED = "delayed"
    NO_PRODUCT = "no_product"
    OUTAGE = "outage"


@dataclass(frozen=True, slots=True)
class FireDetection:
    """One provider-normalized satellite fire detection."""

    provider: str
    satellite: str
    product: str
    timestamp: datetime
    latitude: float
    longitude: float
    frp_mw: float | None = None
    frp_uncertainty_mw: float | None = None
    confidence: float | None = None
    classification: str | int | None = None
    quality: str | int | None = None
    fire_temperature_k: float | None = None
    fire_area_km2: float | None = None
    temporal_filtered: bool | None = None
    source_resolution_km: float | None = None
    source_detection_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderSnapshot:
    """One complete provider product normalized for common processing."""

    provider: str
    satellite: str
    product: str
    product_timestamp: datetime
    received_timestamp: datetime
    status: ProviderStatus
    source_url: str
    filename: str
    detections: tuple[FireDetection, ...]


@dataclass(slots=True)
class FireCluster:
    """A spatial group of fire detections from one provider snapshot."""

    latitude: float
    longitude: float
    distance_km: float
    confidence: float
    frp_mw: float
    acquired: datetime
    pixel_count: int
    track_id: str | None = None
    peak_frp_mw: float | None = None
    place_name: str | None = None
    nearest_settlement: str | None = None
    location_description: str | None = None
    place_attribution: str | None = None

    def attrs(self) -> dict[str, Any]:
        """Return bounded Home Assistant state attributes."""
        attrs = {
            ATTR_LATITUDE: round(self.latitude, 6),
            ATTR_LONGITUDE: round(self.longitude, 6),
            ATTR_DISTANCE_KM: round(self.distance_km, 2),
            ATTR_CONFIDENCE: round(self.confidence, 3),
            ATTR_FRP_MW: round(self.frp_mw, 2),
            ATTR_ACQUIRED: self.acquired.isoformat(),
            ATTR_PIXEL_COUNT: self.pixel_count,
        }
        if self.track_id is not None:
            attrs[ATTR_TRACK_ID] = self.track_id
        if self.peak_frp_mw is not None:
            attrs[ATTR_PEAK_FRP_MW] = round(self.peak_frp_mw, 2)
        if self.place_name is not None:
            attrs[ATTR_PLACE_NAME] = self.place_name
        if self.nearest_settlement is not None:
            attrs[ATTR_NEAREST_SETTLEMENT] = self.nearest_settlement
        if self.location_description is not None:
            attrs[ATTR_LOCATION_DESCRIPTION] = self.location_description
        if self.place_attribution is not None:
            attrs[ATTR_PLACE_ATTRIBUTION] = self.place_attribution
        return attrs
