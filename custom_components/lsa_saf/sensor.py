"""Sensors for LSA SAF."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfLength, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LsaSafConfigEntry
from .entity import LsaSafEntity, LsaSafFireRiskEntity
from .products.fire_risk import WMS_URL


async def async_setup_entry(
    hass: HomeAssistant, entry: LsaSafConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(
        [
            NearestFireSensor(entry),
            ActiveFireCountSensor(entry),
            RawPixelCountSensor(entry),
            ProductTimeSensor(entry),
            ProductAgeSensor(entry),
            FireRiskTodaySensor(entry),
        ]
    )


class NearestFireSensor(LsaSafEntity, SensorEntity):
    _attr_translation_key = "nearest_fire"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:fire-alert"

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_nearest_fire"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data or not data.active_clusters:
            return None
        return round(data.active_clusters[0].distance_km, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if not data or not data.active_clusters:
            return None
        return data.active_clusters[0].attrs() | {"source_url": data.source_url}


class ActiveFireCountSensor(LsaSafEntity, SensorEntity):
    _attr_translation_key = "active_fire_count"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:fire"

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_active_fire_count"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.active_clusters) if self.coordinator.data else 0


class RawPixelCountSensor(LsaSafEntity, SensorEntity):
    _attr_translation_key = "raw_pixel_count"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:dots-hexagon"

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_raw_pixel_count"

    @property
    def native_value(self) -> int:
        return self.coordinator.data.raw_pixels_in_radius if self.coordinator.data else 0


class ProductTimeSensor(LsaSafEntity, SensorEntity):
    _attr_translation_key = "product_time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:satellite-variant"

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_product_time"

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.data.product_time if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        return {"filename": self.coordinator.data.filename, "source_url": self.coordinator.data.source_url}


class ProductAgeSensor(LsaSafEntity, SensorEntity):
    _attr_translation_key = "product_age"
    _attr_native_unit_of_measurement = "min"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_icon = "mdi:timer-sand"

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_product_age"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return max(0, (datetime.now(UTC) - self.coordinator.data.product_time).total_seconds() / 60)


class FireRiskTodaySensor(LsaSafFireRiskEntity, SensorEntity):
    """Current-day maximum sampled FRMv3 risk with the ten-day outlook."""

    _attr_translation_key = "fire_risk_today"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["low", "moderate", "high", "very_high", "extreme", "unknown"]
    _attr_icon = "mdi:pine-tree-fire"

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_fire_risk_today"

    @property
    def native_value(self) -> str:
        data = self.coordinator.data
        return data.days[0].risk if data and data.days else "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if data is None:
            return {"forecast": [], "attribution": "EUMETSAT / LSA SAF, CC BY 4.0"}
        return {
            "risk_level": data.days[0].level,
            "sample_latitude": data.latitude,
            "sample_longitude": data.longitude,
            "generated_at": data.generated_at.isoformat(),
            "forecast": [
                {"date": day.valid_date.isoformat(), "risk": day.risk, "level": day.level}
                for day in data.days
            ],
            "source_url": WMS_URL,
            "attribution": "EUMETSAT / LSA SAF, CC BY 4.0",
        }
