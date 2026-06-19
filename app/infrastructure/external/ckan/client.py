"""Adapter HTTP CKAN pour la couche infrastructure."""

import time
from collections.abc import Callable

import httpx

from app.application.errors.ingestion import CkanRateLimitError, CkanTimeoutError
from app.application.ports.ckan_payloads import parse_package_search_response
from app.application.ports.ckan_types import CkanPackageSearchResponse
from app.core.config import get_settings


class CkanHttpClient:
    """Interroge CKAN et renvoie un payload deja verrouille pour l'application."""

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        max_retries: int = 3,
        backoff_base_seconds: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        settings = get_settings()
        self._base_url = settings.ckan_base_url.rstrip("/")
        self._client = http_client or httpx.Client(timeout=30.0)
        self._max_retries = max_retries
        self._backoff_base_seconds = backoff_base_seconds
        self._sleep = sleep

    def fetch_packages_batch(self, start: int, rows: int = 100) -> CkanPackageSearchResponse:
        """Recupere une page ``package_search`` puis valide sa forme JSON."""

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.get(
                    f"{self._base_url}/api/3/action/package_search",
                    params={"start": start, "rows": rows},
                    follow_redirects=True,
                )
                response.raise_for_status()
                return parse_package_search_response(response.json())
            except httpx.TimeoutException as exc:
                raise CkanTimeoutError("Timeout CKAN sur package_search") from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 429:
                    raise
                if attempt >= self._max_retries:
                    raise CkanRateLimitError("Rate limit CKAN persistant apres retries") from exc

                delay = self._backoff_base_seconds * (2**attempt)
                self._sleep(delay)

        raise CkanRateLimitError("Rate limit CKAN persistant apres retries")
