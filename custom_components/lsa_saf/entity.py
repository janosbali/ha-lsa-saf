"""Base entity helpers."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LsaSafConfigEntry
from .const import DOMAIN, NAME
from .coordinator import LsaSafCoordinator


class LsaSafEntity(CoordinatorEntity[LsaSafCoordinator]):
    """Base entity for LSA SAF."""

    _attr_has_entity_name = True

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="EUMETSAT / LSA SAF",
            model="Satellite products",
            configuration_url="https://lsa-saf.eumetsat.int/en/data/products/",
        )
