"""Safe client and models for the public LSA SAF FRMv3 WMS."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import json
import math
import re
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

PRODUCT_ID = "FRMv3"
LSA_ID = "LSA-504.3"
WMS_DATASET = "MSG-FRMv3"
WMS_URL = "https://adaguc.lsasvcs.ipma.pt/adaguc-server"
FORECAST_DAYS = 10
TIMEOUT = ClientTimeout(total=20, connect=5, sock_read=15)
MAX_JSON_BYTES = 32 * 1024
MAX_MAP_BYTES = 2 * 1024 * 1024
USER_AGENT = "ha-lsa-saf/0.2.4 (https://github.com/janosbali/ha-lsa-saf)"
EUROPE_BOUNDS = (-9.975, 34.475, 45.525, 69.975)
LOCAL_SAMPLE_RADIUS_KM = 10.0

RISK_NAMES = {1: "low", 2: "moderate", 3: "high", 4: "very_high", 5: "extreme"}
RISK_PATTERN = re.compile(r"^(?:[a-z_ ]+)\(([1-5])\)$", re.IGNORECASE)


class FireRiskError(Exception):
    """An FRMv3 request or response was invalid."""


@dataclass(frozen=True, slots=True)
class FireRiskDay:
    """One daily FRMv3 forecast value."""

    valid_date: date
    level: int | None

    @property
    def risk(self) -> str:
        return RISK_NAMES.get(self.level, "unknown")


@dataclass(frozen=True, slots=True)
class FireRiskForecast:
    """Local ten-day forecast plus today's maximum in the monitoring area."""

    latitude: float
    longitude: float
    generated_at: datetime
    days: tuple[FireRiskDay, ...]
    area_level: int | None
    area_latitude: float
    area_longitude: float
    radius_km: float

    @property
    def area_risk(self) -> str:
        return RISK_NAMES.get(self.area_level, "unknown")


class FireRiskClient:
    """Read bounded FRMv3 values and map images from the official WMS host."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def async_forecast(
        self, latitude: float, longitude: float, radius_km: float
    ) -> FireRiskForecast:
        """Retrieve a near-Home forecast and today's monitoring-area maximum."""
        _validate_coordinate(latitude, longitude)
        if not math.isfinite(radius_km) or not 1 <= radius_km <= 500:
            raise FireRiskError("Fire-risk radius is outside the valid range")
        dates = _forecast_dates(datetime.now(UTC))
        local: tuple[float, float, int] | None = None
        for sample_lat, sample_lon in _sample_points(
            latitude, longitude, min(radius_km, LOCAL_SAMPLE_RADIUS_KM)
        ):
            level = await self._async_point(sample_lat, sample_lon, dates[0])
            if level is not None:
                local = (sample_lat, sample_lon, level)
                break
        area_best = local
        seen = (
            {(round(local[0], 6), round(local[1], 6))}
            if local is not None
            else set()
        )
        for sample_lat, sample_lon in _sample_points(latitude, longitude, radius_km):
            key = (round(sample_lat, 6), round(sample_lon, 6))
            if key in seen:
                continue
            seen.add(key)
            level = await self._async_point(sample_lat, sample_lon, dates[0])
            if level is not None and (area_best is None or level > area_best[2]):
                area_best = (sample_lat, sample_lon, level)

        if local is None:
            values = [None] * len(dates)
            local_latitude, local_longitude = latitude, longitude
        else:
            values = [local[2]]
            for valid_date in dates[1:]:
                values.append(await self._async_point(local[0], local[1], valid_date))
            local_latitude, local_longitude = local[0], local[1]
        area_latitude = area_best[0] if area_best else latitude
        area_longitude = area_best[1] if area_best else longitude
        area_level = area_best[2] if area_best else None
        return FireRiskForecast(
            local_latitude, local_longitude, datetime.now(UTC),
            tuple(FireRiskDay(value, level) for value, level in zip(dates, values, strict=True)),
            area_level, area_latitude, area_longitude, radius_km,
        )

    async def _async_point(self, latitude: float, longitude: float, valid_date: date) -> int | None:
        delta = 0.05
        payload = await self._async_get(
            {
                "DATASET": WMS_DATASET, "SERVICE": "WMS", "VERSION": "1.1.1",
                "REQUEST": "GetFeatureInfo", "LAYERS": "Risk", "QUERY_LAYERS": "Risk",
                "STYLES": "risk_map_style/nearest", "SRS": "EPSG:4326",
                "BBOX": f"{longitude-delta},{latitude-delta},{longitude+delta},{latitude+delta}",
                "WIDTH": "101", "HEIGHT": "101", "X": "50", "Y": "50",
                "TIME": f"{valid_date.isoformat()}T12:00:00Z",
                "INFO_FORMAT": "application/json", "FORMAT": "image/png",
            },
            MAX_JSON_BYTES,
        )
        return parse_feature_info(payload, valid_date)

    async def async_map(self, bbox: tuple[float, float, float, float], valid_date: date) -> bytes:
        """Download one bounded forecast map image."""
        west, south, east, north = bbox
        if not (west < east and south < north):
            raise FireRiskError("Invalid fire-risk map bounds")
        image = await self._async_get(
            {
                "DATASET": WMS_DATASET, "SERVICE": "WMS", "VERSION": "1.1.1",
                "REQUEST": "GetMap", "LAYERS": "Risk", "STYLES": "risk_map_style/nearest",
                "SRS": "EPSG:4326", "BBOX": f"{west},{south},{east},{north}",
                "WIDTH": "768", "HEIGHT": "512", "TRANSPARENT": "TRUE",
                "TIME": f"{valid_date.isoformat()}T12:00:00Z", "FORMAT": "image/png",
            },
            MAX_MAP_BYTES,
        )
        if not image.startswith(b"\x89PNG\r\n\x1a\n"):
            raise FireRiskError("FRMv3 map response is not a PNG image")
        return image

    async def _async_get(self, params: dict[str, str], limit: int) -> bytes:
        try:
            async with self._session.get(
                WMS_URL, params=params, headers={"User-Agent": USER_AGENT},
                allow_redirects=False, timeout=TIMEOUT,
            ) as response:
                if response.status != 200:
                    raise FireRiskError("FRMv3 service returned an error")
                if response.content_length is not None and response.content_length > limit:
                    raise FireRiskError("FRMv3 response exceeds the safety limit")
                data = bytearray()
                async for chunk in response.content.iter_chunked(16 * 1024):
                    data.extend(chunk)
                    if len(data) > limit:
                        raise FireRiskError("FRMv3 response exceeds the safety limit")
                return bytes(data)
        except FireRiskError:
            raise
        except (ClientError, TimeoutError) as err:
            raise FireRiskError("FRMv3 service is unavailable") from err


def parse_feature_info(payload: bytes, valid_date: date) -> int | None:
    """Parse the small ADAGUC JSON response without trusting human labels."""
    try:
        parsed: Any = json.loads(payload)
        raw = parsed[0]["data"][f"{valid_date.isoformat()}T12:00:00Z"]
    except (UnicodeDecodeError, json.JSONDecodeError, IndexError, KeyError, TypeError) as err:
        raise FireRiskError("FRMv3 response has an unexpected shape") from err
    if raw == "nodata":
        return None
    if not isinstance(raw, str) or not (match := RISK_PATTERN.fullmatch(raw.strip())):
        raise FireRiskError("FRMv3 response contains an unknown risk level")
    return int(match.group(1))


def _forecast_dates(now: datetime) -> tuple[date, ...]:
    return tuple(now.date() + timedelta(days=offset) for offset in range(FORECAST_DAYS))


def _sample_points(
    latitude: float, longitude: float, radius_km: float
) -> tuple[tuple[float, float], ...]:
    """Return a bounded center-and-compass sample without leaving Europe."""
    distance = radius_km * 0.7
    lat_delta = distance / 110.574
    lon_delta = distance / (
        111.320 * max(0.2, abs(math.cos(math.radians(latitude))))
    )
    offsets = (
        (0, 0), (lat_delta, 0), (-lat_delta, 0), (0, lon_delta), (0, -lon_delta),
        (lat_delta, lon_delta), (lat_delta, -lon_delta),
        (-lat_delta, lon_delta), (-lat_delta, -lon_delta),
    )
    return tuple(
        (
            max(-90.0, min(90.0, latitude + dy)),
            ((longitude + dx + 180) % 360) - 180,
        )
        for dy, dx in offsets
    )


def _validate_coordinate(latitude: float, longitude: float) -> None:
    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise FireRiskError("Latitude is outside the valid range")
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise FireRiskError("Longitude is outside the valid range")


def map_bounds(
    latitude: float, longitude: float, radius_km: float
) -> tuple[float, float, float, float]:
    """Build Europe-clamped WMS bounds around Home."""
    _validate_coordinate(latitude, longitude)
    if not math.isfinite(radius_km) or not 1 <= radius_km <= 500:
        raise FireRiskError("Fire-risk radius is outside the valid range")
    west_limit, south_limit, east_limit, north_limit = EUROPE_BOUNDS
    lat_delta = radius_km / 110.574
    lon_delta = radius_km / (
        111.320 * max(0.2, abs(math.cos(math.radians(latitude))))
    )
    bounds = (
        max(west_limit, longitude - lon_delta),
        max(south_limit, latitude - lat_delta),
        min(east_limit, longitude + lon_delta),
        min(north_limit, latitude + lat_delta),
    )
    if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
        raise FireRiskError("Home is outside the FRMv3 European coverage")
    return bounds
