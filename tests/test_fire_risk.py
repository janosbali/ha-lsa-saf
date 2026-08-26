"""Tests for FRMv3 response validation and sampling."""
from __future__ import annotations

from datetime import date
import json

import pytest

from custom_components.lsa_saf.products.fire_risk import (
    FireRiskError,
    _sample_points,
    map_bounds,
    parse_feature_info,
)


def _payload(value: str) -> bytes:
    return json.dumps([{"data": {"2026-08-26T12:00:00Z": value}}]).encode()


@pytest.mark.parametrize(
    ("value", "expected"),
    [("low (1)", 1), ("moderate (2)", 2), ("high (3)", 3),
     ("very high (4)", 4), ("extreme (5)", 5), ("nodata", None)],
)
def test_parse_feature_info(value: str, expected: int | None) -> None:
    assert parse_feature_info(_payload(value), date(2026, 8, 26)) == expected


@pytest.mark.parametrize("payload", [b"not json", b"[]", _payload("unknown (9)")])
def test_parse_feature_info_rejects_invalid_data(payload: bytes) -> None:
    with pytest.raises(FireRiskError):
        parse_feature_info(payload, date(2026, 8, 26))


def test_sampling_is_bounded() -> None:
    points = _sample_points(47.5, 19.0, 500)

    assert len(points) == 9
    assert points[0] == (47.5, 19.0)
    assert all(-90 <= lat <= 90 and -180 <= lon <= 180 for lat, lon in points)


def test_map_bounds_are_clamped_to_europe() -> None:
    west, south, east, north = map_bounds(47.5, 19.0, 500)

    assert -9.975 <= west < east <= 45.525
    assert 34.475 <= south < north <= 69.975


def test_map_bounds_reject_location_outside_coverage() -> None:
    with pytest.raises(FireRiskError):
        map_bounds(-33.9, 151.2, 25)


@pytest.mark.parametrize("radius", [0, 501, float("nan"), float("inf")])
def test_map_bounds_reject_invalid_radius(radius: float) -> None:
    with pytest.raises(FireRiskError):
        map_bounds(47.5, 19.0, radius)
