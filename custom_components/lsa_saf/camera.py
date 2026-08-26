"""Image entity for the selected FRMv3 forecast map."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import logging

from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LsaSafConfigEntry
from .const import (
    CONF_FIRE_RISK_DAY,
    CONF_RADIUS_KM,
    DEFAULT_FIRE_RISK_DAY,
    DEFAULT_RADIUS_KM,
)
from .entity import LsaSafFireRiskEntity
from .products.fire_risk import FireRiskError, map_bounds

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LsaSafConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([FireRiskMapCamera(entry)])


class FireRiskMapCamera(LsaSafFireRiskEntity, Camera):
    """Display one selected day from the official FRMv3 WMS."""

    _attr_translation_key = "fire_risk_map"
    _attr_icon = "mdi:map-clock"

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        LsaSafFireRiskEntity.__init__(self, entry)
        Camera.__init__(self)
        self.content_type = "image/png"
        self._attr_unique_id = f"{entry.entry_id}_fire_risk_map"
        self._cached_key: tuple[date, float] | None = None
        self._cached_image: bytes | None = None
        self._cached_at: datetime | None = None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        day = int(self.entry.options.get(CONF_FIRE_RISK_DAY, DEFAULT_FIRE_RISK_DAY))
        valid_date = datetime.now(UTC).date() + timedelta(days=day)
        radius = float(self.entry.options.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM))
        key = (valid_date, radius)
        if (
            self._cached_key == key
            and self._cached_at is not None
            and datetime.now(UTC) - self._cached_at < timedelta(hours=1)
        ):
            return self._cached_image
        try:
            bbox = map_bounds(
                float(self.hass.config.latitude),
                float(self.hass.config.longitude),
                radius,
            )
            image = await self.entry.runtime_data.fire_risk_client.async_map(
                bbox, valid_date
            )
        except FireRiskError as err:
            _LOGGER.debug("Could not retrieve FRMv3 map: %s", err)
            return self._cached_image
        self._cached_key = key
        self._cached_image = image
        self._cached_at = datetime.now(UTC)
        return image
