"""Shared LSA SAF Data Service HTTP client."""
from __future__ import annotations

from aiohttp import BasicAuth, ClientSession


class LsaSafError(Exception):
    """Base LSA SAF error."""


class LsaSafAuthError(LsaSafError):
    """Authentication error."""


class LsaSafApi:
    """Shared authenticated client for the LSA SAF Data Service.

    Credentials are kept only in the Home Assistant config entry and in the
    aiohttp BasicAuth object used by this runtime client. The plaintext
    password is intentionally not copied to a separate instance attribute.
    """

    def __init__(self, session: ClientSession, username: str, password: str) -> None:
        self._session = session
        self._auth = BasicAuth(username, password)
