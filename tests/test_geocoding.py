"""Tests for bounded and privacy-conscious reverse geocoding."""
from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta
import json

import pytest

from custom_components.lsa_saf.geocoding import (
    MAX_RESPONSE_BYTES,
    NOMINATIM_ATTRIBUTION,
    PlaceLookupError,
    PlaceNameResolver,
    _cache_key,
    _cached_place,
    _read_limited_json,
    parse_place_info,
    validate_geocoding_url,
)


class _Content:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    async def iter_chunked(self, _size: int):
        yield self.payload


class _Response:
    def __init__(self, payload: bytes, content_length: int | None = None) -> None:
        self.content = _Content(payload)
        self.content_length = content_length


def test_parse_named_feature_and_nearest_settlement() -> None:
    place = parse_place_info(
        {"name": "Kiskunsági Nemzeti Park", "address": {"town": "Kecskemét"}}
    )

    assert place.place_name == "Kiskunsági Nemzeti Park"
    assert place.nearest_settlement == "Kecskemét"
    assert place.location_description == (
        "Kiskunsági Nemzeti Park – tűz Kecskemét közelében"
    )
    assert place.attribution == NOMINATIM_ATTRIBUTION


def test_parse_settlement_fallback_and_sanitizes_text() -> None:
    place = parse_place_info({"address": {"village": "  Novi\n  Sad  "}})

    assert place.place_name is None
    assert place.nearest_settlement == "Novi Sad"
    assert place.location_description == "Novi Sad közelében észlelt tűz"


def test_parse_unknown_location_has_safe_fallback() -> None:
    place = parse_place_info({"display_name": "ignored unbounded display name"})

    assert place.place_name is None
    assert place.nearest_settlement is None
    assert place.location_description == "Műholdas tűzdetektálás"


async def test_bounded_json_reader_accepts_small_object() -> None:
    payload = json.dumps({"name": "Test"}).encode()

    assert await _read_limited_json(_Response(payload)) == {"name": "Test"}


@pytest.mark.parametrize(
    "response",
    [
        _Response(b"{}", content_length=MAX_RESPONSE_BYTES + 1),
        _Response(b"x" * (MAX_RESPONSE_BYTES + 1)),
        _Response(b"not-json"),
        _Response(b"[]"),
    ],
)
async def test_bounded_json_reader_rejects_unsafe_responses(response) -> None:
    with pytest.raises(PlaceLookupError):
        await _read_limited_json(response)


@pytest.mark.parametrize(
    "url",
    [
        "http://geo.example/reverse",
        "https://user:secret@geo.example/reverse",
        "https://geo.example/search",
        "https://geo.example/reverse?token=secret",
        "https://geo.example/reverse#fragment",
    ],
)
def test_geocoding_url_validation_rejects_unsafe_endpoints(url: str) -> None:
    with pytest.raises(ValueError):
        validate_geocoding_url(url)


def test_geocoding_url_validation_normalizes_base_url() -> None:
    assert validate_geocoding_url(" https://geo.example/ ") == (
        "https://geo.example/reverse"
    )


def test_coordinate_cache_is_shared_and_expires() -> None:
    assert _cache_key(46.12341, 20.98761) == _cache_key(46.12349, 20.98759)
    now = datetime.now(UTC)
    entry = {
        "resolved_at": now.isoformat(),
        "place": {
            "place_name": None,
            "nearest_settlement": "Szeged",
            "location_description": "Szeged közelében észlelt tűz",
            "attribution": "© OpenStreetMap contributors, ODbL",
        },
    }

    assert _cached_place(entry, now).nearest_settlement == "Szeged"
    assert _cached_place(entry, now + timedelta(days=91)) is None


def test_hourly_budget_prunes_only_expired_requests() -> None:
    resolver = object.__new__(PlaceNameResolver)
    now = datetime.now(UTC)
    resolver._request_times = deque(
        [now - timedelta(hours=2), now - timedelta(minutes=30)]
    )

    resolver._prune_request_times(now)

    assert list(resolver._request_times) == [now - timedelta(minutes=30)]
