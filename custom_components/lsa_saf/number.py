"""Adjustable monitoring radius entity."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LsaSafConfigEntry
from .const import CONF_RADIUS_KM, DEFAULT_RADIUS_KM, MAX_RADIUS_KM, MIN_RADIUS_KM
from .entity import LsaSafEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: LsaSafConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([MonitoringRadiusNumber(entry)])


class MonitoringRadiusNumber(LsaSafEntity, NumberEntity):
    """Monitoring radius that can be put directly on a dashboard."""

    _attr_translation_key = "monitoring_radius"
    _attr_native_min_value = MIN_RADIUS_KM
    _attr_native_max_value = MAX_RADIUS_KM
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = "km"
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:radius-outline"

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_monitoring_radius"

    @property
    def native_value(self) -> float:
        return float(self.entry.options.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM))

    async def async_set_native_value(self, value: float) -> None:
        options = dict(self.entry.options)
        options[CONF_RADIUS_KM] = float(value)
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
