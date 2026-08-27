"""Active-fire provider adapters."""

from .base import ActiveFireProvider
from .mtg import MtgActiveFireProvider

__all__ = ["ActiveFireProvider", "MtgActiveFireProvider"]
