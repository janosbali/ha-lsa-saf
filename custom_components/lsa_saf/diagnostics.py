"""Privacy-safe diagnostics for the LSA SAF integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import LsaSafConfigEntry
from .const import CONF_PASSWORD, CONF_USERNAME

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: LsaSafConfigEntry
) -> dict[str, Any]:
    """Return a bounded diagnostic summary without location or credentials."""
    active = entry.runtime_data.coordinator
    risk = entry.runtime_data.fire_risk_coordinator
    active_data = active.data
    risk_data = risk.data

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "active_fire": {
            "last_update_success": active.last_update_success,
            "product_time": (
                active_data.product_time.isoformat() if active_data else None
            ),
            "active_cluster_count": (
                len(active_data.active_clusters) if active_data else None
            ),
            "tracked_fire_count": (
                len(active_data.tracked_fires) if active_data else None
            ),
            "raw_pixels_in_radius": (
                active_data.raw_pixels_in_radius if active_data else None
            ),
        },
        "fire_risk": {
            "last_update_success": risk.last_update_success,
            "generated_at": (
                risk_data.generated_at.isoformat() if risk_data else None
            ),
            "forecast_days": len(risk_data.days) if risk_data else None,
            "near_home_risk": (
                risk_data.days[0].risk if risk_data and risk_data.days else None
            ),
            "area_risk": risk_data.area_risk if risk_data else None,
        },
        "place_names_enabled": entry.runtime_data.place_name_resolver is not None,
    }
