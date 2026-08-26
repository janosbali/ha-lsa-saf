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
    PLATFORMS,
)
from .coordinator import LsaSafCoordinator
from .geocoding import PlaceNameResolver
from .products.fire import ActiveFireClient


@dataclass
class RuntimeData:
    """Runtime data for one LSA SAF config entry."""

    coordinator: LsaSafCoordinator


type LsaSafConfigEntry = ConfigEntry[RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: LsaSafConfigEntry) -> bool:
    """Set up LSA SAF from a config entry."""
    session = async_get_clientsession(hass)
    client = ActiveFireClient(session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    resolver = (
        PlaceNameResolver(session)
        if entry.options.get(CONF_RESOLVE_PLACE_NAMES, DEFAULT_RESOLVE_PLACE_NAMES)
        else None
    )
    coordinator = LsaSafCoordinator(hass, entry, client, resolver)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = RuntimeData(coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LsaSafConfigEntry) -> bool:
    """Unload an LSA SAF config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
