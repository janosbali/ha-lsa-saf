"""MTG MTFRPPixel (LSA-509) client and CSV parser."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import csv
import gzip
import io
import math
import re
from typing import Any

from aiohttp import ClientResponseError, ClientSession

from ..api import LsaSafApi, LsaSafAuthError, LsaSafError


class LsaSafNoDataError(LsaSafError):
    """No recent product was found."""


@dataclass(slots=True)
class FirePixel:
    """One detected fire pixel."""

    latitude: float
    longitude: float
    confidence: float
    frp_mw: float
    acquired: datetime
    pixel_size_km2: float | None
    frp_uncertainty_mw: float | None
    abs_line: int | None
    abs_samp: int | None


@dataclass(slots=True)
class Product:
    """Parsed MTFRPPixel list product."""

    filename: str
    url: str
    product_time: datetime
    pixels: list[FirePixel]


BASE_URL = "https://datalsasaf.lsasvcs.ipma.pt/PRODUCTS/MTG/MTFRPPixel/NATIVE"
FILE_PREFIX = "LSA-509_MTG_MTFRPPIXEL-ListProduct_MTG-FD_"
FILE_SUFFIX = ".csv.gz"


class ActiveFireClient(LsaSafApi):
    """Small async client for the LSA SAF HTTPS data service."""

    async def async_test_auth(self) -> None:
        """Validate credentials against an actual MTFRPPixel product request.

        The archive index may be browsable without authentication, so testing
        only the directory page is not sufficient. Fetching the newest product
        verifies the same authenticated path used during normal operation.
        """
        try:
            await self.async_fetch_latest()
        except LsaSafNoDataError:
            # A temporary gap in recent product availability is not an auth failure.
            # Individual probes still return 401/403 immediately when credentials
            # are rejected by the Data Service.
            return

    async def async_fetch_latest(self, now: datetime | None = None) -> Product:
        """Fetch the newest available 10-minute ListProduct.

        MTG products are nominally generated every 10 minutes but are published with
        some latency. We probe deterministic product names backwards in time. This is
        more robust than depending on the h5ai directory UI/HTML implementation.
        """
        now = (now or datetime.now(UTC)).astimezone(UTC)
        rounded = now.replace(minute=(now.minute // 10) * 10, second=0, microsecond=0)

        # Start one slot back; current-slot data cannot be complete yet. Search 4 hours.
        for step in range(1, 25):
            stamp = rounded - timedelta(minutes=10 * step)
            filename = f"{FILE_PREFIX}{stamp:%Y%m%d%H%M}{FILE_SUFFIX}"
            url = f"{BASE_URL}/{stamp:%Y/%m/%d}/{filename}"
            async with self._session.get(url, auth=self._auth) as response:
                if response.status in (401, 403):
                    raise LsaSafAuthError("Invalid or expired LSA SAF credentials")
                if response.status == 404:
                    continue
                try:
                    response.raise_for_status()
                except ClientResponseError as err:
                    raise LsaSafError(f"LSA SAF HTTP error: {err.status}") from err
                payload = await response.read()
                return parse_product(filename, url, payload)

        raise LsaSafNoDataError("No MTFRPPixel ListProduct found in the last 4 hours")


def parse_product(filename: str, url: str, payload: bytes) -> Product:
    """Parse a gzip-compressed MTFRPPixel ListProduct CSV."""
    match = re.search(r"_(\d{12})\.csv\.gz$", filename)
    if not match:
        raise LsaSafError(f"Unrecognized product filename: {filename}")
    product_time = datetime.strptime(match.group(1), "%Y%m%d%H%M").replace(tzinfo=UTC)

    try:
        text = gzip.decompress(payload).decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as err:
        raise LsaSafError("Could not decompress/decode MTFRPPixel product") from err

    reader = csv.DictReader(io.StringIO(text))
    required = {"LATITUDE", "LONGITUDE", "FIRE_CONFIDENCE", "FRP", "ACQTIME"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise LsaSafError("Unexpected MTFRPPixel CSV columns")

    pixels: list[FirePixel] = []
    for row in reader:
        try:
            acquired = datetime.strptime(row["ACQTIME"], "%Y%m%d%H%M%S").replace(tzinfo=UTC)
            lat = _float_or_none(row.get("LATITUDE"))
            lon = _float_or_none(row.get("LONGITUDE"))
            if lat is None or lon is None:
                continue
            pixels.append(
                FirePixel(
                    latitude=lat,
                    longitude=lon,
                    confidence=float(row["FIRE_CONFIDENCE"]),
                    frp_mw=float(row["FRP"]),
                    acquired=acquired,
                    pixel_size_km2=_float_or_none(row.get("PIXEL_SIZE")),
                    frp_uncertainty_mw=_float_or_none(row.get("FRP_UNCERTAINTY")),
                    abs_line=_int_or_none(row.get("ABS_LINE")),
                    abs_samp=_int_or_none(row.get("ABS_SAMP")),
                )
            )
            # Store parallax coordinates on the object without growing the public dataclass.
            # Consumers can reparse them from rows only if needed; v0.1 uses native coords.
        except (TypeError, ValueError):
            continue

    return Product(filename=filename, url=url, product_time=product_time, pixels=pixels)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km."""
    radius = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None
