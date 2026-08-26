"""Map entities for active LSA SAF fire clusters."""
from __future__ import annotations

from typing import Any, override

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LsaSafConfigEntry
from .const import ATTR_PRODUCT_TIME, ATTR_SOURCE_URL, DOMAIN
from .coordinator import FireCluster
from .entity import LsaSafEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LsaSafConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up and maintain one map entity per active fire cluster."""
    coordinator = entry.runtime_data.coordinator
    entities: dict[str, LsaSafFireLocation] = {}

    @callback
    def async_sync_entities() -> None:
        data = coordinator.data
        active = {
            cluster.track_id: cluster
            for cluster in (data.tracked_fires if data else [])
            if cluster.track_id is not None
        }

        for track_id in entities.keys() - active.keys():
            entity = entities.pop(track_id)
            hass.async_create_task(entity.async_remove(force_remove=True))

        new_entities: list[LsaSafFireLocation] = []
        for track_id, cluster in active.items():
            if track_id in entities:
                entities[track_id].set_cluster(cluster)
                continue
            entity = LsaSafFireLocation(entry, cluster)
            entities[track_id] = entity
            new_entities.append(entity)

        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(async_sync_entities))
    async_sync_entities()


class LsaSafFireLocation(LsaSafEntity, GeolocationEvent):
    """An active fire cluster shown on Home Assistant maps."""

    _attr_should_poll = False
    _attr_source = DOMAIN
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:fire-alert"

    def __init__(self, entry: LsaSafConfigEntry, cluster: FireCluster) -> None:
        super().__init__(entry)
        if cluster.track_id is None:
            raise ValueError("A map entity requires a tracked fire cluster")
        self._cluster = cluster
        self._attr_unique_id = f"{entry.entry_id}_fire_{cluster.track_id}"
        self._attr_name = cluster.location_description or f"Fire detection {cluster.track_id[:6]}"

    @callback
    def set_cluster(self, cluster: FireCluster) -> None:
        """Replace this entity's current cluster data."""
        self._cluster = cluster
        self._attr_name = cluster.location_description or f"Fire detection {cluster.track_id[:6]}"

    @property
    @override
    def distance(self) -> float:
        return self._cluster.distance_km

    @property
    @override
    def latitude(self) -> float:
        return self._cluster.latitude

    @property
    @override
    def longitude(self) -> float:
        return self._cluster.longitude

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        attrs = self._cluster.attrs()
        if data:
            attrs[ATTR_PRODUCT_TIME] = data.product_time.isoformat()
            attrs[ATTR_SOURCE_URL] = data.source_url
        return attrs
