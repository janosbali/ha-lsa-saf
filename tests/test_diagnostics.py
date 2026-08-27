"""Tests for privacy-safe diagnostics."""
from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from custom_components.lsa_saf.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.lsa_saf.products.fire_risk import FireRiskDay, FireRiskForecast


@pytest.mark.asyncio
async def test_diagnostics_are_bounded_and_redacted(hass) -> None:
    """Diagnostics expose health/counts but no secrets or precise locations."""
    product_time = datetime(2026, 8, 27, 16, 20, tzinfo=UTC)
    generated_at = datetime(2026, 8, 27, 16, 21, tzinfo=UTC)
    active_data = SimpleNamespace(
        product_time=product_time,
        active_clusters=[object(), object()],
        tracked_fires=[object(), object(), object()],
        raw_pixels_in_radius=4,
        source_url="https://example.invalid/private-product",
    )
    risk_data = FireRiskForecast(
        latitude=46.123456,
        longitude=18.654321,
        generated_at=generated_at,
        days=(FireRiskDay(date(2026, 8, 27), 5),),
        area_level=4,
        area_latitude=46.2,
        area_longitude=18.7,
        radius_km=100,
    )
    entry = SimpleNamespace(
        data={"username": "private-user", "password": "private-password"},
        options={"radius_km": 25.0},
        runtime_data=SimpleNamespace(
            coordinator=SimpleNamespace(data=active_data, last_update_success=True),
            fire_risk_coordinator=SimpleNamespace(
                data=risk_data, last_update_success=True
            ),
            place_name_resolver=object(),
        ),
    )

    result = await async_get_config_entry_diagnostics(hass, entry)
    serialized = repr(result)

    assert result["active_fire"]["active_cluster_count"] == 2
    assert result["active_fire"]["tracked_fire_count"] == 3
    assert result["fire_risk"]["near_home_risk"] == "extreme"
    assert result["fire_risk"]["area_risk"] == "very_high"
    assert "private-user" not in serialized
    assert "private-password" not in serialized
    assert "46.123456" not in serialized
    assert "18.654321" not in serialized
    assert "example.invalid" not in serialized


@pytest.mark.asyncio
async def test_diagnostics_handle_coordinators_without_data(hass) -> None:
    """Diagnostics remain downloadable before optional forecast data arrives."""
    entry = SimpleNamespace(
        data={"username": "user", "password": "password"},
        options={},
        runtime_data=SimpleNamespace(
            coordinator=SimpleNamespace(data=None, last_update_success=False),
            fire_risk_coordinator=SimpleNamespace(
                data=None, last_update_success=False
            ),
            place_name_resolver=None,
        ),
    )

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["active_fire"]["product_time"] is None
    assert result["fire_risk"]["near_home_risk"] is None
    assert result["place_names_enabled"] is False
