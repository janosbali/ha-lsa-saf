"""Regression tests for the provider-neutral active-fire pipeline."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from custom_components.lsa_saf.clustering import cluster_detections
from custom_components.lsa_saf.models import (
    FireDetection,
    ProviderSnapshot,
    ProviderStatus,
)
from custom_components.lsa_saf.products.fire import FirePixel, Product
from custom_components.lsa_saf.providers.mtg import (
    PRODUCT,
    PROVIDER,
    SATELLITE,
    MtgActiveFireProvider,
)


def _detection(**changes) -> FireDetection:
    values = {
        "provider": PROVIDER,
        "satellite": SATELLITE,
        "product": PRODUCT,
        "timestamp": datetime(2026, 8, 27, 16, 20, tzinfo=UTC),
        "latitude": 46.25,
        "longitude": 20.14,
        "frp_mw": 10.0,
        "confidence": 0.8,
    }
    values.update(changes)
    return FireDetection(**values)


def test_provider_snapshot_is_immutable() -> None:
    """Provider results are stable values passed into common processing."""
    snapshot = ProviderSnapshot(
        provider=PROVIDER,
        satellite=SATELLITE,
        product=PRODUCT,
        product_timestamp=datetime(2026, 8, 27, 16, 20, tzinfo=UTC),
        received_timestamp=datetime(2026, 8, 27, 16, 22, tzinfo=UTC),
        status=ProviderStatus.AVAILABLE,
        source_url="https://example.invalid/product",
        filename="product.csv.gz",
        detections=(_detection(),),
    )

    with pytest.raises(AttributeError):
        snapshot.status = ProviderStatus.OUTAGE  # type: ignore[misc]


@pytest.mark.asyncio
async def test_mtg_adapter_preserves_product_values() -> None:
    """The MTG adapter maps every existing parser value without loss."""
    acquired = datetime(2026, 8, 27, 16, 20, 30, tzinfo=UTC)
    product_time = datetime(2026, 8, 27, 16, 20, tzinfo=UTC)
    pixel = FirePixel(
        latitude=46.25,
        longitude=20.14,
        confidence=0.91,
        frp_mw=12.4,
        acquired=acquired,
        pixel_size_km2=1.2,
        frp_uncertainty_mw=2.1,
        abs_line=100,
        abs_samp=200,
    )
    client = AsyncMock()
    client.async_fetch_latest.return_value = Product(
        filename="product.csv.gz",
        url="https://example.invalid/product",
        product_time=product_time,
        pixels=[pixel],
    )

    snapshot = await MtgActiveFireProvider(client).async_fetch_latest()
    detection = snapshot.detections[0]

    assert snapshot.provider == PROVIDER
    assert snapshot.status is ProviderStatus.AVAILABLE
    assert snapshot.product_timestamp == product_time
    assert detection.timestamp == acquired
    assert detection.latitude == pixel.latitude
    assert detection.longitude == pixel.longitude
    assert detection.frp_mw == pixel.frp_mw
    assert detection.frp_uncertainty_mw == pixel.frp_uncertainty_mw
    assert detection.confidence == pixel.confidence
    assert detection.fire_area_km2 == pixel.pixel_size_km2
    assert detection.source_detection_id.endswith(":100:200")


def test_common_clustering_preserves_mtg_aggregation() -> None:
    """Common clustering retains weighted centroid and peak confidence logic."""
    first = _detection(frp_mw=10.0, confidence=0.8)
    second = _detection(
        latitude=46.251,
        longitude=20.141,
        frp_mw=30.0,
        confidence=0.95,
    )

    clusters = cluster_detections(
        [(first, 10.0), (second, 10.1)],
        home_latitude=46.2,
        home_longitude=20.1,
        cluster_radius_km=1.0,
    )

    assert len(clusters) == 1
    assert clusters[0].pixel_count == 2
    assert clusters[0].frp_mw == 40.0
    assert clusters[0].confidence == 0.95
    assert clusters[0].latitude == pytest.approx(46.25075)
    assert clusters[0].longitude == pytest.approx(20.14075)


def test_common_model_accepts_provider_specific_missing_values() -> None:
    """Providers are not forced to invent confidence, FRP, or quality values."""
    detection = _detection(
        frp_mw=None,
        confidence=None,
        quality=None,
        classification=None,
    )

    assert detection.frp_mw is None
    assert detection.confidence is None
