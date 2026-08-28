"""Base entity helpers."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LsaSafConfigEntry
from .const import DOMAIN, NAME
from .coordinator import LsaSafCoordinator
from .fire_risk_coordinator import FireRiskCoordinator
from .lst_coordinator import LandSurfaceTemperatureCoordinator


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
            model="MTG Active Fire / FRMv3",
            configuration_url="https://adaguc.lsasvcs.ipma.pt/",
        )


class LsaSafFireRiskEntity(CoordinatorEntity[FireRiskCoordinator]):
    """Base entity for the daily FRMv3 product."""

    _attr_has_entity_name = True

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        super().__init__(entry.runtime_data.fire_risk_coordinator)
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="EUMETSAT / LSA SAF",
            model="MTG Active Fire / FRMv3",
            configuration_url="https://adaguc.lsasvcs.ipma.pt/",
        )


class LsaSafLandSurfaceTemperatureEntity(
    CoordinatorEntity[LandSurfaceTemperatureCoordinator]
):
    """Base entity for the optional MTLST product."""

    _attr_has_entity_name = True

    def __init__(self, entry: LsaSafConfigEntry) -> None:
        super().__init__(entry.runtime_data.lst_coordinator)
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="EUMETSAT / LSA SAF",
            model="MTG Active Fire / FRMv3 / MTLST",
            configuration_url="https://adaguc.lsasvcs.ipma.pt/",
        )
