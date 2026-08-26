"""Coordinator for the daily LSA SAF FRMv3 forecast."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_RADIUS_KM, DEFAULT_RADIUS_KM, DOMAIN
from .products.fire_risk import FireRiskClient, FireRiskError, FireRiskForecast

_LOGGER = logging.getLogger(__name__)


class FireRiskCoordinator(DataUpdateCoordinator[FireRiskForecast]):
    """Retrieve the demonstration FRMv3 product independently of active fires."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: FireRiskClient
    ) -> None:
        self.entry = entry
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_fire_risk",
            update_interval=timedelta(hours=12),
        )

    async def _async_update_data(self) -> FireRiskForecast:
        try:
            return await self.client.async_forecast(
                float(self.hass.config.latitude),
                float(self.hass.config.longitude),
                float(self.entry.options.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM)),
            )
        except FireRiskError as err:
            raise UpdateFailed(str(err)) from err
