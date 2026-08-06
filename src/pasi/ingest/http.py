"""Shared HTTP helpers for polite, logged public downloads."""

from __future__ import annotations

import hashlib
import time
from typing import Any

import requests
from requests import Response

from pasi.config.settings import Settings, get_settings
from pasi.logging.setup import get_logger

logger = get_logger(__name__)


class HttpError(RuntimeError):
    """Raised when an HTTP request fails after retries."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


class HttpClient:
    """Thin requests wrapper with retries, delays, and configurable User-Agent."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.settings.sec_user_agent,
                "Accept-Encoding": "gzip, deflate",
            }
        )

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        retries: int | None = None,
        expect_json: bool = False,
    ) -> Response:
        timeout = timeout if timeout is not None else self.settings.http_timeout_seconds
        retries = retries if retries is not None else self.settings.http_max_retries
        delay = self.settings.http_request_delay_seconds

        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            if delay > 0 and attempt > 1:
                time.sleep(delay)
            elif delay > 0 and attempt == 1:
                # Polite pacing even on first request when configured.
                time.sleep(min(delay, 0.2))

            try:
                logger.debug("HTTP GET %s (attempt %s/%s)", url, attempt, retries)
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeout,
                )
                if response.status_code >= 500:
                    raise HttpError(
                        f"Server error {response.status_code} for {url}",
                        status_code=response.status_code,
                    )
                if response.status_code >= 400:
                    raise HttpError(
                        f"Client error {response.status_code} for {url}",
                        status_code=response.status_code,
                    )
                if expect_json:
                    # Validate JSON parse early for clearer errors.
                    response.json()
                return response
            except (requests.RequestException, HttpError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "HTTP GET failed for %s on attempt %s/%s: %s",
                    url,
                    attempt,
                    retries,
                    exc,
                )
                if attempt < retries:
                    time.sleep(delay * attempt)

        raise HttpError(f"Failed GET {url}: {last_error}") from last_error
