"""Bounded, cached, and rate-limited reverse geocoding."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import json
from typing import Any
from urllib.parse import urlsplit

from aiohttp import ClientError, ClientSession, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

PUBLIC_NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_ATTRIBUTION = "© OpenStreetMap contributors, ODbL"
GEOCODE_TIMEOUT = ClientTimeout(total=12, connect=5, sock_read=7)
MAX_RESPONSE_BYTES = 64 * 1024
PUBLIC_MIN_INTERVAL_SECONDS = 15.0
CUSTOM_MIN_INTERVAL_SECONDS = 1.0
PUBLIC_REQUESTS_PER_HOUR = 30
CUSTOM_REQUESTS_PER_HOUR = 240
CACHE_TTL = timedelta(days=90)
MAX_CACHE_ENTRIES = 5000
USER_AGENT = "ha-lsa-saf/0.1.7 (https://github.com/janosbali/ha-lsa-saf)"
STORE_VERSION = 1


class PlaceLookupError(Exception):
    """A reverse-geocoding lookup could not be completed safely."""


class PlaceLookupRateLimited(PlaceLookupError):
    """The local request budget or remote backoff is active."""


@dataclass(frozen=True, slots=True)
class PlaceInfo:
    """Sanitized place information for a fire coordinate."""

    place_name: str | None
    nearest_settlement: str | None
    location_description: str
    attribution: str = NOMINATIM_ATTRIBUTION


def validate_geocoding_url(value: str) -> str:
    """Validate and normalize a user-configured Nominatim reverse endpoint."""
    url = value.strip()
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("The geocoding endpoint must be a clean HTTPS URL")
    path = parsed.path.rstrip("/")
    if path and not path.endswith("/reverse"):
        raise ValueError("The geocoding endpoint must end in /reverse")
    return url.rstrip("/") + ("/reverse" if not path else "")


class PlaceNameResolver:
    """Resolve fire coordinates with durable caching and local quotas."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: ClientSession,
        entry_id: str,
        endpoint: str,
    ) -> None:
        self._session = session
        self._endpoint = validate_geocoding_url(endpoint)
        public = self._endpoint == PUBLIC_NOMINATIM_URL
        self._min_interval = PUBLIC_MIN_INTERVAL_SECONDS if public else CUSTOM_MIN_INTERVAL_SECONDS
        self._hourly_limit = PUBLIC_REQUESTS_PER_HOUR if public else CUSTOM_REQUESTS_PER_HOUR
        self._store = Store(hass, STORE_VERSION, f"lsa_saf.{entry_id}.place_cache")
        self._cache: dict[str, dict[str, Any]] = {}
        self._request_times: deque[datetime] = deque()
        self._lock = asyncio.Lock()
        self._last_request_time = 0.0
        self._backoff_until = 0.0

    async def async_setup(self) -> None:
        """Load and prune the durable coordinate cache."""
        stored = await self._store.async_load()
        if isinstance(stored, dict) and isinstance(stored.get("entries"), dict):
            self._cache = stored["entries"]
            requests = stored.get("requests", [])
            if not isinstance(requests, list):
                requests = []
            for value in requests:
                try:
                    timestamp = datetime.fromisoformat(str(value))
                    self._request_times.append(
                        timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
                    )
                except (TypeError, ValueError):
                    continue
        now = datetime.now(UTC)
        self._prune_cache(now)
        self._prune_request_times(now)

    async def async_resolve(self, latitude: float, longitude: float) -> PlaceInfo:
        """Resolve one coordinate, using cache before any network request."""
        key = _cache_key(latitude, longitude)
        now = datetime.now(UTC)
        if cached := _cached_place(self._cache.get(key), now):
            return cached
        async with self._lock:
            now = datetime.now(UTC)
            if cached := _cached_place(self._cache.get(key), now):
                return cached
            loop = asyncio.get_running_loop()
            monotonic_now = loop.time()
            if monotonic_now < self._backoff_until:
                raise PlaceLookupRateLimited("Place-name service backoff is active")
            self._prune_request_times(now)
            if len(self._request_times) >= self._hourly_limit:
                raise PlaceLookupRateLimited("Hourly place-name request limit reached")
            delay = self._min_interval - (monotonic_now - self._last_request_time)
            if delay > 0:
                await asyncio.sleep(delay)
            place = await self._async_request(latitude, longitude)
            self._request_times.append(now)
            self._cache[key] = {"resolved_at": now.isoformat(), "place": asdict(place)}
            self._prune_cache(now)
            await self._store.async_save(
                {
                    "entries": self._cache,
                    "requests": [value.isoformat() for value in self._request_times],
                }
            )
            return place

    async def _async_request(self, latitude: float, longitude: float) -> PlaceInfo:
        loop = asyncio.get_running_loop()
        try:
            async with self._session.get(
                self._endpoint,
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
                if response.status == 429 or response.status >= 500:
                    self._backoff_until = loop.time() + 3600
                    raise PlaceLookupRateLimited("Place-name service requested a retry later")
                if response.status != 200:
                    self._backoff_until = loop.time() + 3600
                    raise PlaceLookupError("Place-name service returned an error")
                return parse_place_info(await _read_limited_json(response))
        except PlaceLookupError:
            raise
        except (ClientError, TimeoutError) as err:
            self._backoff_until = loop.time() + 300
            raise PlaceLookupError("Place-name service is unavailable") from err

    def _prune_cache(self, now: datetime) -> None:
        self._cache = {
            key: value for key, value in self._cache.items() if _cache_entry_fresh(value, now)
        }
        if len(self._cache) > MAX_CACHE_ENTRIES:
            ordered = sorted(
                self._cache.items(),
                key=lambda item: str(item[1].get("resolved_at", "")),
                reverse=True,
            )
            self._cache = dict(ordered[:MAX_CACHE_ENTRIES])

    def _prune_request_times(self, now: datetime) -> None:
        while self._request_times and now - self._request_times[0] >= timedelta(hours=1):
            self._request_times.popleft()


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
        address, "city", "town", "village", "municipality", "hamlet", "suburb", "county"
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
    return PlaceInfo(feature_name, settlement, description)


def _cache_key(latitude: float, longitude: float) -> str:
    return f"{latitude:.3f},{longitude:.3f}"


def _cache_entry_fresh(entry: Any, now: datetime) -> bool:
    if not isinstance(entry, dict):
        return False
    try:
        resolved = datetime.fromisoformat(str(entry["resolved_at"]))
    except (KeyError, TypeError, ValueError):
        return False
    if resolved.tzinfo is None:
        resolved = resolved.replace(tzinfo=UTC)
    age = now - resolved
    return timedelta(0) <= age <= CACHE_TTL


def _cached_place(entry: Any, now: datetime) -> PlaceInfo | None:
    if not _cache_entry_fresh(entry, now):
        return None
    place = entry.get("place")
    if not isinstance(place, dict):
        return None
    description = _clean_text(place.get("location_description"))
    if description is None:
        return None
    return PlaceInfo(
        place_name=_clean_text(place.get("place_name")),
        nearest_settlement=_clean_text(place.get("nearest_settlement")),
        location_description=description,
        attribution=_clean_text(place.get("attribution")) or NOMINATIM_ATTRIBUTION,
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
