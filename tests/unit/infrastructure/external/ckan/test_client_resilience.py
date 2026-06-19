"""Tests de resilience du client CKAN HTTP."""

from __future__ import annotations

import httpx
import pytest

from app.application.errors.ingestion import CkanRateLimitError, CkanTimeoutError
from app.infrastructure.external.ckan.client import CkanHttpClient


def test_client_retries_with_exponential_backoff_on_429() -> None:
    """Un 429 declenche un backoff exponentiel puis un succes possible."""

    attempts = {"count": 0}
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            return httpx.Response(status_code=429, request=request, json={"error": "rate_limit"})
        return httpx.Response(status_code=200, request=request, json={"result": {"results": []}})

    client = CkanHttpClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler), timeout=1.0),
        max_retries=3,
        backoff_base_seconds=0.25,
        sleep=sleeps.append,
    )

    payload = client.fetch_packages_batch(start=0, rows=100)

    assert payload.get("result", {}).get("results") == []
    assert attempts["count"] == 3
    assert sleeps == [0.25, 0.5]


def test_client_raises_rate_limit_error_after_exhausted_retries() -> None:
    """Apres tous les retries 429, une erreur applicative explicite est levee."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=429, request=request, json={"error": "rate_limit"})

    client = CkanHttpClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler), timeout=1.0),
        max_retries=2,
        backoff_base_seconds=0.1,
        sleep=lambda _: None,
    )

    try:
        client.fetch_packages_batch(start=0, rows=100)
    except CkanRateLimitError:
        pass
    else:
        raise AssertionError("CkanRateLimitError attendu")


def test_client_raises_timeout_error_on_http_timeout() -> None:
    """Un timeout transport CKAN est mappe vers une erreur applicative."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    client = CkanHttpClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler), timeout=1.0),
        sleep=lambda _: None,
    )

    try:
        client.fetch_packages_batch(start=0, rows=100)
    except CkanTimeoutError:
        pass
    else:
        raise AssertionError("CkanTimeoutError attendu")


def test_client_re_raises_non_429_http_errors() -> None:
    """Les statuts HTTP hors 429 ne sont pas convertis en erreur applicative."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=500, request=request, json={"error": "server_error"})

    client = CkanHttpClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler), timeout=1.0),
        sleep=lambda _: None,
    )

    with pytest.raises(httpx.HTTPStatusError):
        client.fetch_packages_batch(start=0, rows=100)


def test_client_follows_redirects() -> None:
    """Le client suit une redirection HTTP avant de parser le payload final."""

    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(
                status_code=302,
                request=request,
                headers={"location": "https://ckan.opendata.swiss/api/3/action/package_search"},
            )
        return httpx.Response(status_code=200, request=request, json={"result": {"results": []}})

    client = CkanHttpClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler), timeout=1.0),
        sleep=lambda _: None,
    )

    payload = client.fetch_packages_batch(start=0, rows=100)

    assert payload.get("result", {}).get("results") == []
    assert calls["count"] == 2
