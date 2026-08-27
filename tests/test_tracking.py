"""Tests for persistent fire incident lifecycle tracking."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.lsa_saf.models import FireCluster, FireLifecycle
from custom_components.lsa_saf.tracking import update_incidents

BASE = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


def _cluster(at: datetime = BASE, **changes) -> FireCluster:
    values = {
        "latitude": 46.0,
        "longitude": 20.0,
        "distance_km": 25.0,
        "confidence": 0.8,
        "frp_mw": 10.0,
        "acquired": at,
        "pixel_count": 2,
    }
    values.update(changes)
    return FireCluster(**values)


def test_new_incident_has_stable_id_and_initial_aggregates() -> None:
    cluster = _cluster()

    result = update_incidents(
        [], [cluster], now=BASE, matching_radius_km=3.0, memory_hours=6
    )

    incident = result.incidents[0]
    assert len(result.new_incidents) == 1
    assert cluster.lifecycle is FireLifecycle.NEW
    assert cluster.track_id == incident["track_id"]
    assert incident["first_seen"] == BASE.isoformat()
    assert incident["minimum_distance_km"] == 25.0
    assert incident["maximum_frp_mw"] == 10.0
    assert incident["maximum_pixel_count"] == 2
    assert incident["detections_total"] == 2
    assert incident["frp_trend"] == "unknown"
    assert incident["trend_sample_count"] == 1


def test_continuing_incident_updates_current_and_maximum_values() -> None:
    first = update_incidents(
        [], [_cluster()], now=BASE, matching_radius_km=3.0, memory_hours=6
    )
    incident_id = first.incidents[0]["track_id"]
    later = BASE + timedelta(minutes=10)
    cluster = _cluster(
        later,
        latitude=46.005,
        distance_km=23.0,
        confidence=0.9,
        frp_mw=25.0,
        pixel_count=4,
    )

    result = update_incidents(
        first.incidents,
        [cluster],
        now=later,
        matching_radius_km=3.0,
        memory_hours=6,
    )

    incident = result.incidents[0]
    assert result.new_incidents == []
    assert incident["track_id"] == incident_id
    assert cluster.lifecycle is FireLifecycle.CONTINUING
    assert incident["minimum_distance_km"] == 23.0
    assert incident["maximum_frp_mw"] == 25.0
    assert incident["maximum_confidence"] == 0.9
    assert incident["maximum_pixel_count"] == 4
    assert incident["detections_total"] == 6


def test_same_product_does_not_double_count_detections() -> None:
    first = update_incidents(
        [], [_cluster()], now=BASE, matching_radius_km=3.0, memory_hours=6
    )

    repeated = update_incidents(
        first.incidents,
        [_cluster()],
        now=BASE + timedelta(minutes=5),
        matching_radius_km=3.0,
        memory_hours=6,
    )

    assert repeated.incidents[0]["detections_total"] == 2


def test_missing_detection_becomes_inactive_but_is_not_ended() -> None:
    first = update_incidents(
        [], [_cluster()], now=BASE, matching_radius_km=3.0, memory_hours=6
    )

    result = update_incidents(
        first.incidents,
        [],
        now=BASE + timedelta(minutes=10),
        matching_radius_km=3.0,
        memory_hours=6,
    )

    assert result.incidents[0]["lifecycle"] == FireLifecycle.INACTIVE.value
    assert result.ended_incident_ids == []


def test_incident_ends_only_after_memory_window() -> None:
    first = update_incidents(
        [], [_cluster()], now=BASE, matching_radius_km=3.0, memory_hours=6
    )

    result = update_incidents(
        first.incidents,
        [],
        now=BASE + timedelta(hours=6, seconds=1),
        matching_radius_km=3.0,
        memory_hours=6,
    )

    assert result.incidents == []
    assert result.ended_incident_ids


def test_legacy_persisted_track_is_migrated_and_continued() -> None:
    legacy = {
        "track_id": "legacy-id",
        "latitude": 46.0,
        "longitude": 20.0,
        "first_seen": BASE.isoformat(),
        "last_seen": BASE.isoformat(),
        "peak_frp_mw": 12.0,
        "frp_mw": 12.0,
        "confidence": 0.7,
        "pixel_count": 1,
    }
    later = BASE + timedelta(minutes=10)

    result = update_incidents(
        [legacy],
        [_cluster(later)],
        now=later,
        matching_radius_km=3.0,
        memory_hours=6,
    )

    incident = result.incidents[0]
    assert incident["track_id"] == "legacy-id"
    assert incident["lifecycle"] == FireLifecycle.CONTINUING.value
    assert incident["maximum_frp_mw"] == 12.0
    assert incident["detections_total"] == 3
