"""Tests for bounded and privacy-conscious reverse geocoding."""
from __future__ import annotations

import json

import pytest

from custom_components.lsa_saf.geocoding import (
    MAX_RESPONSE_BYTES,
    NOMINATIM_ATTRIBUTION,
    PlaceLookupError,
    _read_limited_json,
    parse_place_info,
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
