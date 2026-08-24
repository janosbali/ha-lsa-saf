"""Coordinator for the LSA SAF active-fire product."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LsaSafAuthError, LsaSafError
from .products.fire import ActiveFireClient, FirePixel, haversine_km
from .const import (
    ATTR_ACQUIRED,
    ATTR_CONFIDENCE,
    ATTR_DISTANCE_KM,
    ATTR_FRP_MW,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_PEAK_FRP_MW,
    ATTR_PIXEL_COUNT,
    ATTR_PRODUCT_TIME,
    ATTR_SOURCE_URL,
    ATTR_TRACK_ID,
    BUS_EVENT_NEW_FIRE,
    CONF_DEDUP_HOURS,
    CONF_DEDUP_RADIUS_KM,
    CONF_MIN_CONFIDENCE,
    CONF_MIN_FRP_MW,
    CONF_RADIUS_KM,
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_DEDUP_HOURS,
    DEFAULT_DEDUP_RADIUS_KM,
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_MIN_FRP_MW,
    DEFAULT_RADIUS_KM,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
STORE_VERSION = 1


@dataclass(slots=True)
class FireCluster:
    """A small group of adjacent fire pixels in one MTG product."""

    latitude: float
    longitude: float
    distance_km: float
    confidence: float
    frp_mw: float
    acquired: datetime
    pixel_count: int

    def attrs(self) -> dict[str, Any]:
        return {
            ATTR_LATITUDE: round(self.latitude, 6),
            ATTR_LONGITUDE: round(self.longitude, 6),
            ATTR_DISTANCE_KM: round(self.distance_km, 2),
            ATTR_CONFIDENCE: round(self.confidence, 3),
            ATTR_FRP_MW: round(self.frp_mw, 2),
            ATTR_ACQUIRED: self.acquired.isoformat(),
            ATTR_PIXEL_COUNT: self.pixel_count,
        }


@dataclass(slots=True)
class CoordinatorData:
    """Data published to Home Assistant entities."""

    product_time: datetime
    source_url: str
    filename: str
    active_clusters: list[FireCluster]
    new_fires: list[dict[str, Any]]
    raw_pixels_in_radius: int


class LsaSafCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Fetch, filter, cluster, and deduplicate MTG fire detections."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: ActiveFireClient) -> None:
        self.entry = entry
        self.client = client
        self._store = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}.tracks")
        self._tracks: list[dict[str, Any]] = []
        self._store_loaded = False
        self._initialized = False
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=int(entry.options.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES))
            ),
        )

    async def _async_setup(self) -> None:
        stored = await self._store.async_load()
        if isinstance(stored, dict) and isinstance(stored.get("tracks"), list):
            self._tracks = stored["tracks"]
            self._initialized = bool(stored.get("initialized", True))
        self._store_loaded = True

    async def _async_update_data(self) -> CoordinatorData:
        try:
            product = await self.client.async_fetch_latest()
        except LsaSafAuthError as err:
            raise ConfigEntryAuthFailed from err
        except LsaSafError as err:
            raise UpdateFailed(str(err)) from err

        radius_km = float(self.entry.options.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM))
        min_conf = float(self.entry.options.get(CONF_MIN_CONFIDENCE, DEFAULT_MIN_CONFIDENCE))
        min_frp = float(self.entry.options.get(CONF_MIN_FRP_MW, DEFAULT_MIN_FRP_MW))
        dedup_radius = float(self.entry.options.get(CONF_DEDUP_RADIUS_KM, DEFAULT_DEDUP_RADIUS_KM))
        dedup_hours = int(self.entry.options.get(CONF_DEDUP_HOURS, DEFAULT_DEDUP_HOURS))
        home_lat = float(self.hass.config.latitude)
        home_lon = float(self.hass.config.longitude)

        filtered: list[tuple[FirePixel, float]] = []
        for pixel in product.pixels:
            if pixel.confidence < min_conf or pixel.frp_mw < min_frp:
                continue
            distance = haversine_km(home_lat, home_lon, pixel.latitude, pixel.longitude)
            if distance <= radius_km:
                filtered.append((pixel, distance))

        clusters = _cluster_pixels(filtered, home_lat, home_lon, max(0.5, dedup_radius * 0.66))
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=dedup_hours)
        self._tracks = [t for t in self._tracks if _parse_dt(t.get("last_seen")) >= cutoff]

        new_fires: list[dict[str, Any]] = []
        changed = False
        first_snapshot = not self._initialized
        for cluster in clusters:
            matched: dict[str, Any] | None = None
            for track in self._tracks:
                if haversine_km(cluster.latitude, cluster.longitude, float(track["latitude"]), float(track["longitude"])) <= dedup_radius:
                    matched = track
                    break

            if matched is None:
                track_id = hashlib.blake2s(
                    f"{cluster.latitude:.4f}:{cluster.longitude:.4f}:{cluster.acquired.isoformat()}".encode(),
                    digest_size=6,
                ).hexdigest()
                matched = {
                    "track_id": track_id,
                    "latitude": cluster.latitude,
                    "longitude": cluster.longitude,
                    "first_seen": cluster.acquired.isoformat(),
                    "last_seen": cluster.acquired.isoformat(),
                    "peak_frp_mw": cluster.frp_mw,
                }
                self._tracks.append(matched)
                attrs = cluster.attrs() | {
                    ATTR_TRACK_ID: track_id,
                    ATTR_SOURCE_URL: product.url,
                    ATTR_PRODUCT_TIME: product.product_time.isoformat(),
                    ATTR_PEAK_FRP_MW: round(cluster.frp_mw, 2),
                }
                if not first_snapshot:
                    new_fires.append(attrs)
                    self.hass.bus.async_fire(BUS_EVENT_NEW_FIRE, attrs)
                changed = True
            else:
                matched["latitude"] = cluster.latitude
                matched["longitude"] = cluster.longitude
                matched["last_seen"] = cluster.acquired.isoformat()
                matched["peak_frp_mw"] = max(float(matched.get("peak_frp_mw", 0)), cluster.frp_mw)
                changed = True

        if first_snapshot:
            self._initialized = True
            changed = True

        if changed and self._store_loaded:
            await self._store.async_save({"initialized": self._initialized, "tracks": self._tracks})

        return CoordinatorData(
            product_time=product.product_time,
            source_url=product.url,
            filename=product.filename,
            active_clusters=clusters,
            new_fires=new_fires,
            raw_pixels_in_radius=len(filtered),
        )


def _cluster_pixels(
    pixels: list[tuple[FirePixel, float]], home_lat: float, home_lon: float, cluster_radius_km: float
) -> list[FireCluster]:
    """Greedily group adjacent fire pixels from the same product."""
    groups: list[list[FirePixel]] = []
    for pixel, _distance in sorted(pixels, key=lambda item: item[0].frp_mw, reverse=True):
        target: list[FirePixel] | None = None
        for group in groups:
            ref = group[0]
            if haversine_km(pixel.latitude, pixel.longitude, ref.latitude, ref.longitude) <= cluster_radius_km:
                target = group
                break
        if target is None:
            groups.append([pixel])
        else:
            target.append(pixel)

    result: list[FireCluster] = []
    for group in groups:
        total_frp = sum(p.frp_mw for p in group)
        if total_frp > 0:
            lat = sum(p.latitude * p.frp_mw for p in group) / total_frp
            lon = sum(p.longitude * p.frp_mw for p in group) / total_frp
        else:
            lat = sum(p.latitude for p in group) / len(group)
            lon = sum(p.longitude for p in group) / len(group)
        result.append(
            FireCluster(
                latitude=lat,
                longitude=lon,
                distance_km=haversine_km(home_lat, home_lon, lat, lon),
                confidence=max(p.confidence for p in group),
                frp_mw=total_frp,
                acquired=max(p.acquired for p in group),
                pixel_count=len(group),
            )
        )
    return sorted(result, key=lambda c: c.distance_km)


def _parse_dt(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=UTC)
