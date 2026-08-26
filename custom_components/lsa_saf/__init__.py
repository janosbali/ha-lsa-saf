"""LSA SAF integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_PASSWORD,
    CONF_RESOLVE_PLACE_NAMES,
    CONF_USERNAME,
    DEFAULT_RESOLVE_PLACE_NAMES,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import LsaSafCoordinator
from .fire_risk_coordinator import FireRiskCoordinator
from .geocoding import PlaceNameResolver
from .products.fire import ActiveFireClient
from .products.fire_risk import FireRiskClient


@dataclass
class RuntimeData:
    """Runtime data for one LSA SAF config entry."""

    coordinator: LsaSafCoordinator
    fire_risk_coordinator: FireRiskCoordinator
    fire_risk_client: FireRiskClient


type LsaSafConfigEntry = ConfigEntry[RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: LsaSafConfigEntry) -> bool:
    """Set up LSA SAF from a config entry."""
    session = async_get_clientsession(hass)
    client = ActiveFireClient(session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    resolver = None
    if entry.options.get(CONF_RESOLVE_PLACE_NAMES, DEFAULT_RESOLVE_PLACE_NAMES):
        resolver = PlaceNameResolver(hass)
        await resolver.async_setup()
    coordinator = LsaSafCoordinator(hass, entry, client, resolver)
    await coordinator.async_config_entry_first_refresh()
    fire_risk_client = FireRiskClient(session)
    fire_risk_coordinator = FireRiskCoordinator(hass, entry, fire_risk_client)
    entry.runtime_data = RuntimeData(
        coordinator=coordinator,
        fire_risk_coordinator=fire_risk_coordinator,
        fire_risk_client=fire_risk_client,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_create_background_task(
        hass,
        fire_risk_coordinator.async_refresh(),
        f"{DOMAIN} initial FRMv3 forecast",
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LsaSafConfigEntry) -> bool:
    """Unload an LSA SAF config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
