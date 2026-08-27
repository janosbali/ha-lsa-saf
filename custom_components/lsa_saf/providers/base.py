"""Interface implemented by active-fire data providers."""
from __future__ import annotations

from typing import Protocol

from ..models import ProviderSnapshot


class ActiveFireProvider(Protocol):
    """Return provider data in the common active-fire model."""

    async def async_fetch_latest(self) -> ProviderSnapshot:
        """Fetch and normalize the latest provider product."""
        ...
