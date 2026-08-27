"""Persistent, provider-neutral fire incident tracking."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
from typing import Any

from .clustering import haversine_km
from .models import FireCluster, FireLifecycle


@dataclass(slots=True)
class TrackingResult:
    """Result of applying one valid provider snapshot to incident state."""

    incidents: list[dict[str, Any]]
    new_incidents: list[tuple[dict[str, Any], FireCluster]]
    ended_incident_ids: list[str]
    changed: bool


def update_incidents(
    incidents: list[dict[str, Any]],
    clusters: list[FireCluster],
    *,
    now: datetime,
    matching_radius_km: float,
    memory_hours: int,
) -> TrackingResult:
    """Match clusters to incidents and update bounded lifecycle aggregates."""
    cutoff = now - timedelta(hours=memory_hours)
    retained: list[dict[str, Any]] = []
    ended: list[str] = []
    changed = False
    for incident in incidents:
        _migrate_incident(incident)
        if _parse_dt(incident.get("last_seen")) < cutoff:
            incident["lifecycle"] = FireLifecycle.ENDED.value
            ended.append(str(incident.get("track_id", "")))
            changed = True
            continue
        if incident.get("lifecycle") != FireLifecycle.INACTIVE.value:
            incident["lifecycle"] = FireLifecycle.INACTIVE.value
            changed = True
        retained.append(incident)

    new_incidents: list[tuple[dict[str, Any], FireCluster]] = []
    matched_ids: set[str] = set()
    for cluster in clusters:
        matched = _nearest_match(
            retained, cluster, matching_radius_km, matched_ids
        )
        if matched is None:
            matched = _new_incident(cluster)
            retained.append(matched)
            new_incidents.append((matched, cluster))
        else:
            _update_incident(matched, cluster)
        matched_ids.add(str(matched["track_id"]))
        apply_incident_metadata(cluster, matched)
        changed = True

    return TrackingResult(retained, new_incidents, ended, changed)


def apply_incident_metadata(cluster: FireCluster, incident: dict[str, Any]) -> None:
    """Copy bounded incident aggregates onto an entity-ready cluster."""
    cluster.track_id = str(incident["track_id"])
    cluster.peak_frp_mw = float(incident["maximum_frp_mw"])
    cluster.lifecycle = FireLifecycle(str(incident["lifecycle"]))
    cluster.first_seen = _parse_dt(incident["first_seen"])
    cluster.last_seen = _parse_dt(incident["last_seen"])
    cluster.minimum_distance_km = float(incident["minimum_distance_km"])
    cluster.maximum_frp_mw = float(incident["maximum_frp_mw"])
    cluster.maximum_pixel_count = int(incident["maximum_pixel_count"])
    cluster.detections_total = int(incident["detections_total"])
    cluster.maximum_confidence = float(incident["maximum_confidence"])


def _nearest_match(
    incidents: list[dict[str, Any]],
    cluster: FireCluster,
    radius_km: float,
    matched_ids: set[str],
) -> dict[str, Any] | None:
    candidates = (
        (
            haversine_km(
                cluster.latitude,
                cluster.longitude,
                float(incident["latitude"]),
                float(incident["longitude"]),
            ),
            incident,
        )
        for incident in incidents
        if str(incident.get("track_id")) not in matched_ids
    )
    within = [item for item in candidates if item[0] <= radius_km]
    return min(within, key=lambda item: item[0])[1] if within else None


def _new_incident(cluster: FireCluster) -> dict[str, Any]:
    incident_id = hashlib.blake2s(
        f"{cluster.latitude:.4f}:{cluster.longitude:.4f}:{cluster.acquired.isoformat()}".encode(),
        digest_size=6,
    ).hexdigest()
    return {
        "track_id": incident_id,
        "latitude": cluster.latitude,
        "longitude": cluster.longitude,
        "first_seen": cluster.acquired.isoformat(),
        "last_seen": cluster.acquired.isoformat(),
        "lifecycle": FireLifecycle.NEW.value,
        "frp_mw": cluster.frp_mw,
        "peak_frp_mw": cluster.frp_mw,
        "maximum_frp_mw": cluster.frp_mw,
        "confidence": cluster.confidence,
        "maximum_confidence": cluster.confidence,
        "pixel_count": cluster.pixel_count,
        "maximum_pixel_count": cluster.pixel_count,
        "detections_total": cluster.pixel_count,
        "minimum_distance_km": cluster.distance_km,
    }


def _update_incident(incident: dict[str, Any], cluster: FireCluster) -> None:
    previous_last_seen = _parse_dt(incident["last_seen"])
    is_new_observation = cluster.acquired > previous_last_seen
    incident.update(
        {
            "latitude": cluster.latitude,
            "longitude": cluster.longitude,
            "last_seen": max(previous_last_seen, cluster.acquired).isoformat(),
            "lifecycle": FireLifecycle.CONTINUING.value,
            "frp_mw": cluster.frp_mw,
            "confidence": cluster.confidence,
            "pixel_count": cluster.pixel_count,
            "minimum_distance_km": min(
                float(incident.get("minimum_distance_km", cluster.distance_km)),
                cluster.distance_km,
            ),
            "maximum_frp_mw": max(
                float(incident["maximum_frp_mw"]), cluster.frp_mw
            ),
            "peak_frp_mw": max(
                float(incident["maximum_frp_mw"]), cluster.frp_mw
            ),
            "maximum_confidence": max(
                float(incident["maximum_confidence"]), cluster.confidence
            ),
            "maximum_pixel_count": max(
                int(incident["maximum_pixel_count"]), cluster.pixel_count
            ),
        }
    )
    if is_new_observation:
        incident["detections_total"] = (
            int(incident["detections_total"]) + cluster.pixel_count
        )


def _migrate_incident(incident: dict[str, Any]) -> None:
    """Populate lifecycle fields for legacy v1 track records."""
    incident.setdefault("lifecycle", FireLifecycle.CONTINUING.value)
    incident.setdefault("maximum_frp_mw", incident.get("peak_frp_mw", incident.get("frp_mw", 0)))
    incident.setdefault("peak_frp_mw", incident["maximum_frp_mw"])
    incident.setdefault("maximum_confidence", incident.get("confidence", 0))
    incident.setdefault("maximum_pixel_count", incident.get("pixel_count", 0))
    incident.setdefault("detections_total", incident.get("pixel_count", 0))


def _parse_dt(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=UTC)
