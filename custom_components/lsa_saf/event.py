"""Event entity for newly detected MTG fires."""
from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LsaSafConfigEntry
from .const import EVENT_NEW_FIRE
from .entity import LsaSafEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: LsaSafConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([NewFireEvent(entry)])


class NewFireEvent(LsaSafEntity, EventEntity):
    """Event emitted once for each newly deduplicated nearby fire."""

    _attr_translation_key = "new_fire"
    _attr_event_types = [EVENT_NEW_FIRE]
    _attr_icon = "mdi:fire-alert"

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_new_fire"
        self._last_product_filename: str | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if data and data.filename != self._last_product_filename:
            self._last_product_filename = data.filename
            for fire in data.new_fires:
                self._trigger_event(EVENT_NEW_FIRE, fire)
                self.async_write_ha_state()
        super()._handle_coordinator_update()
