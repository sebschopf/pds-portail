"""Tests d'integration des endpoints PDS-89 (webhook Polar, watchers, alerts)."""

from __future__ import annotations

import hmac
import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.infrastructure.persistence.changelog_repository import SqlAlchemyChangeLogRepository
from app.infrastructure.persistence.watcher_repository import SqlAlchemyWatcherRepository

from ._fixtures import configure_api_modules, populate_cache_nominale


@pytest.fixture
def watchers_api_ctx(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> dict[str, Any]:
    """Contexte API isole pour les endpoints watchers/webhook."""

    db_url = f"sqlite:///{tmp_path / 'test-watchers.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("POLAR_WEBHOOK_SECRET", "polar-secret-test")
    monkeypatch.setenv("POLAR_API_KEY", "polar-api-key-test")
    monkeypatch.setenv("POLAR_ORGANIZATION_ID", "org-test")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    dataset_id, _ = populate_cache_nominale(cache_repository)

    return {
        "app": app,
        "dataset_id": dataset_id,
        "secret": "polar-secret-test",
    }


def _signed_header(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()
    return f"sha256={digest}"


def test_webhook_order_created_creates_watcher(watchers_api_ctx: dict[str, Any]) -> None:
    """POST /api/v1/webhooks/polar traite order.created et crée une surveillance."""

    app = watchers_api_ctx["app"]
    dataset_id = watchers_api_ctx["dataset_id"]
    secret = watchers_api_ctx["secret"]
    payload: dict[str, Any] = {
        "id": "evt-order-created-001",
        "type": "order.created",
        "data": {
            "customer_email": "watcher@example.com",
            "subscription_id": "sub_001",
            "metadata": {"dataset_id": dataset_id},
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    client = cast(Any, TestClient(app))
    response = cast(
        Response,
        client.post(
            "/api/v1/webhooks/polar",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Polar-Signature": _signed_header(secret, body),
            },
        ),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    watcher_repo = SqlAlchemyWatcherRepository()
    watcher = watcher_repo.find_by_email("watcher@example.com")
    assert watcher is not None
    watched = [
        item for item in watcher_repo.list_watched_datasets() if item.watcher_id == watcher.id
    ]
    assert len(watched) == 1
    assert watched[0].dataset_id == dataset_id


def test_webhook_subscription_cancelled_suspends_watcher(
    watchers_api_ctx: dict[str, Any],
) -> None:
    """POST /api/v1/webhooks/polar traite subscription.cancelled et suspend le watcher."""

    app = watchers_api_ctx["app"]
    secret = watchers_api_ctx["secret"]

    watcher_repo = SqlAlchemyWatcherRepository()
    watcher_repo.create(
        email="cancelled@example.com",
        token="9e2966c7-0d95-4684-8067-7f6d1f5aaf8b",
        polar_subscription_id="sub_cancelled_001",
    )

    payload: dict[str, Any] = {
        "id": "evt-sub-cancelled-001",
        "type": "subscription.cancelled",
        "data": {"subscription_id": "sub_cancelled_001"},
        "timestamp": datetime.now(UTC).isoformat(),
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    client = cast(Any, TestClient(app))
    response = cast(
        Response,
        client.post(
            "/api/v1/webhooks/polar",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Polar-Signature": _signed_header(secret, body),
            },
        ),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    updated = watcher_repo.find_by_polar_subscription_id("sub_cancelled_001")
    assert updated is not None
    assert updated.status == "suspended"


def test_watchers_get_and_delete_flow(watchers_api_ctx: dict[str, Any]) -> None:
    """POST/GET/DELETE /api/v1/watchers fonctionne avec token UUID."""

    app = watchers_api_ctx["app"]
    dataset_id = watchers_api_ctx["dataset_id"]
    client = cast(Any, TestClient(app))

    create_response = cast(
        Response,
        client.post(
            "/api/v1/watchers",
            json={
                "email": "manual@example.com",
                "dataset_id": dataset_id,
            },
        ),
    )
    assert create_response.status_code == 200
    token = create_response.json()["token"]

    list_response = cast(Response, client.get(f"/api/v1/watchers?token={token}"))
    assert list_response.status_code == 200
    assert list_response.json()["email"] == "manual@example.com"
    assert len(list_response.json()["items"]) == 1

    watched_id = list_response.json()["items"][0]["id"]
    delete_response = cast(Response, client.delete(f"/api/v1/watchers/{watched_id}?token={token}"))
    assert delete_response.status_code == 204

    list_after_delete = cast(Response, client.get(f"/api/v1/watchers?token={token}"))
    assert list_after_delete.status_code == 200
    assert list_after_delete.json()["items"] == []


def test_alerts_endpoint_returns_history_for_watched_dataset(
    watchers_api_ctx: dict[str, Any],
) -> None:
    """GET /api/v1/alerts retourne l'historique trié des datasets surveillés."""

    app = watchers_api_ctx["app"]
    dataset_id = watchers_api_ctx["dataset_id"]
    client = cast(Any, TestClient(app))

    create_response = cast(
        Response,
        client.post(
            "/api/v1/watchers",
            json={
                "email": "alerts@example.com",
                "dataset_id": dataset_id,
            },
        ),
    )
    assert create_response.status_code == 200
    token = create_response.json()["token"]

    changelog_repo = SqlAlchemyChangeLogRepository()
    changelog_repo.insert(
        dataset_id=dataset_id,
        change_type="quality_score",
        previous_value="70",
        new_value="82",
        detected_at="2026-07-04T00:00:00+00:00",
    )

    alerts_response = cast(Response, client.get(f"/api/v1/alerts?token={token}"))
    assert alerts_response.status_code == 200
    payload = alerts_response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["dataset_id"] == dataset_id
    assert payload["items"][0]["change_type"] == "quality_score"


def test_invalid_token_rejected_for_watchers_and_alerts(
    watchers_api_ctx: dict[str, Any],
) -> None:
    """Token invalide => endpoints protégés watchers/alerts rejettent en 401."""

    app = watchers_api_ctx["app"]
    client = cast(Any, TestClient(app))

    bad_watchers = cast(Response, client.get("/api/v1/watchers?token=invalid-token"))
    assert bad_watchers.status_code == 401

    bad_alerts = cast(Response, client.get("/api/v1/alerts?token=invalid-token"))
    assert bad_alerts.status_code == 401
