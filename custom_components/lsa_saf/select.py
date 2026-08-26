"""Forecast-day selector for the FRMv3 map."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LsaSafConfigEntry
from .const import CONF_FIRE_RISK_DAY, DEFAULT_FIRE_RISK_DAY
from .entity import LsaSafFireRiskEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LsaSafConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([FireRiskForecastDaySelect(entry)])


class FireRiskForecastDaySelect(LsaSafFireRiskEntity, SelectEntity):
    """Choose which daily forecast the map camera displays."""

    _attr_translation_key = "fire_risk_day"
    _attr_options = [str(day) for day in range(10)]
    _attr_icon = "mdi:calendar-range"

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_fire_risk_day"

    @property
    def current_option(self) -> str:
        return str(self.entry.options.get(CONF_FIRE_RISK_DAY, DEFAULT_FIRE_RISK_DAY))

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ValueError("Unsupported FRMv3 forecast day")
        options = dict(self.entry.options)
        options[CONF_FIRE_RISK_DAY] = int(option)
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        self.async_write_ha_state()
