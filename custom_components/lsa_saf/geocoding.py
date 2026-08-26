"""Rate-limited reverse geocoding for public fire coordinates."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_ATTRIBUTION = "© OpenStreetMap contributors, ODbL"
GEOCODE_TIMEOUT = ClientTimeout(total=12, connect=5, sock_read=7)
MAX_RESPONSE_BYTES = 64 * 1024
MIN_REQUEST_INTERVAL_SECONDS = 15.0
USER_AGENT = "ha-lsa-saf/0.1.6 (https://github.com/janosbali/ha-lsa-saf)"


class PlaceLookupError(Exception):
    """A reverse-geocoding lookup could not be completed safely."""


@dataclass(frozen=True, slots=True)
class PlaceInfo:
    """Sanitized place information for a fire coordinate."""

    place_name: str | None
    nearest_settlement: str | None
    location_description: str
    attribution: str = NOMINATIM_ATTRIBUTION


class PlaceNameResolver:
    """Resolve fire coordinates without exceeding the public API policy."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._lock = asyncio.Lock()
        self._last_request_time = 0.0

    async def async_resolve(self, latitude: float, longitude: float) -> PlaceInfo:
        """Resolve one coordinate, serializing requests to four per minute."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            delay = MIN_REQUEST_INTERVAL_SECONDS - (loop.time() - self._last_request_time)
            if delay > 0:
                await asyncio.sleep(delay)
            try:
                async with self._session.get(
                    NOMINATIM_URL,
                    params={
                        "format": "jsonv2",
                        "lat": f"{latitude:.6f}",
                        "lon": f"{longitude:.6f}",
                        "zoom": "15",
                        "addressdetails": "1",
                        "layer": "address",
                    },
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "application/json",
                        "Accept-Language": "hu,en;q=0.8",
                    },
                    allow_redirects=False,
                    timeout=GEOCODE_TIMEOUT,
                ) as response:
                    self._last_request_time = loop.time()
                    if response.status != 200:
                        raise PlaceLookupError("Place-name service returned an error")
                    payload = await _read_limited_json(response)
            except PlaceLookupError:
                raise
            except (ClientError, TimeoutError) as err:
                raise PlaceLookupError("Place-name service is unavailable") from err
        return parse_place_info(payload)


async def _read_limited_json(response: Any) -> dict[str, Any]:
    """Read a small JSON response without trusting Content-Length."""
    if response.content_length is not None and response.content_length > MAX_RESPONSE_BYTES:
        raise PlaceLookupError("Place-name response exceeds the safety limit")
    payload = bytearray()
    async for chunk in response.content.iter_chunked(8 * 1024):
        payload.extend(chunk)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise PlaceLookupError("Place-name response exceeds the safety limit")
    try:
        parsed = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise PlaceLookupError("Place-name response is invalid") from err
    if not isinstance(parsed, dict):
        raise PlaceLookupError("Place-name response has an unexpected shape")
    return parsed


def parse_place_info(payload: dict[str, Any]) -> PlaceInfo:
    """Extract a named location and nearest settlement from Nominatim JSON."""
    address = payload.get("address")
    if not isinstance(address, dict):
        address = {}

    settlement = _first_text(
        address,
        "city",
        "town",
        "village",
        "municipality",
        "hamlet",
        "suburb",
        "county",
    )
    feature_name = _clean_text(payload.get("name"))
    if feature_name and settlement and feature_name.casefold() != settlement.casefold():
        description = f"{feature_name} – tűz {settlement} közelében"
    elif settlement:
        description = f"{settlement} közelében észlelt tűz"
    elif feature_name:
        description = f"Tűz {feature_name} közelében"
    else:
        description = "Műholdas tűzdetektálás"

    return PlaceInfo(
        place_name=feature_name,
        nearest_settlement=settlement,
        location_description=description,
    )


def _first_text(values: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        if text := _clean_text(values.get(key)):
            return text
    return None


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned[:160] if cleaned else None
