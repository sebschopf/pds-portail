from __future__ import annotations

import hmac
import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Protocol, cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.infrastructure.persistence.watcher_repository import SqlAlchemyWatcherRepository

from ._fixtures import configure_api_modules, populate_cache_nominale


@pytest.fixture
def support_api_ctx(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> dict[str, Any]:
    """Contexte API isole pour les endpoints support internes."""

    db_url = f"sqlite:///{tmp_path / 'support-internal.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("INTERNAL_API_TOKEN", "support-token-test")
    monkeypatch.setenv("POLAR_WEBHOOK_SECRET", "polar-secret-test")
    monkeypatch.setenv("POLAR_API_KEY", "polar-api-key-test")
    monkeypatch.setenv("POLAR_ORGANIZATION_ID", "org-test")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "smtp-user-test")
    monkeypatch.setenv("SMTP_PASSWORD", "smtp-password-test")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.test")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    dataset_id, _ = populate_cache_nominale(cache_repository)

    return {
        "app": app,
        "dataset_id": dataset_id,
        "internal_token": "support-token-test",
        "secret": "polar-secret-test",
    }


def _signed_header(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()
    return f"sha256={digest}"


def _support_headers(token: str, request_id: str = "req-support-001") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Operator-Id": "support-agent-1",
        "X-Request-Id": request_id,
    }


class _SupportHttpClient(Protocol):
    def get(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response: ...

    def post(
        self,
        url: str,
        *,
        content: bytes | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Response: ...


class _FakeSMTP:
    instances: list[_FakeSMTP] = []

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.sent_messages: list[Any] = []
        self.started_tls = False
        self.logged_in = False
        _FakeSMTP.instances.append(self)

    def __enter__(self) -> _FakeSMTP:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def starttls(self, context: object | None = None) -> None:
        del context
        self.started_tls = True

    def login(self, _user: str, _password: str) -> None:
        self.logged_in = True

    def send_message(self, message: Any) -> None:
        self.sent_messages.append(message)


def _create_watcher_via_webhook(
    client: _SupportHttpClient,
    dataset_id: str,
    secret: str,
    email: str,
    subscription_id: str,
) -> Response:
    payload: dict[str, Any] = {
        "id": f"evt-{email}",
        "type": "order.created",
        "data": {
            "customer_email": email,
            "subscription_id": subscription_id,
            "metadata": {"dataset_id": dataset_id},
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return client.post(
        "/api/v1/webhooks/polar",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Polar-Signature": _signed_header(secret, body),
        },
    )


def _cancel_subscription_webhook(
    client: _SupportHttpClient,
    secret: str,
    subscription_id: str,
) -> Response:
    payload: dict[str, Any] = {
        "id": f"evt-cancel-{subscription_id}",
        "type": "subscription.cancelled",
        "data": {"subscription_id": subscription_id},
        "timestamp": datetime.now(UTC).isoformat(),
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return client.post(
        "/api/v1/webhooks/polar",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Polar-Signature": _signed_header(secret, body),
        },
    )


def test_internal_support_diagnostic_returns_redacted_fields_and_webhook_history(
    support_api_ctx: dict[str, Any],
) -> None:
    """Le diagnostic support par email reste protégé et redige."""

    app = support_api_ctx["app"]
    dataset_id = support_api_ctx["dataset_id"]
    secret = support_api_ctx["secret"]
    token = support_api_ctx["internal_token"]
    email = "watcher-support@example.ch"
    subscription_id = "sub_support_001"
    client = cast(_SupportHttpClient, TestClient(app))

    create_response = _create_watcher_via_webhook(
        client, dataset_id, secret, email, subscription_id
    )
    assert create_response.status_code == 200

    response = client.get(
        f"/api/v1/internal/support/watchers/by-email?email={email}",
        headers=_support_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["watcher_status"] == "active"
    assert payload["subscription_id_present"] is True
    assert payload["watched_datasets_count"] == 1
    assert payload["last_webhook_at"] is not None
    assert payload["last_magic_link_at"] is not None
    assert set(payload) == {
        "watcher_id",
        "watcher_status",
        "subscription_id_present",
        "watched_datasets_count",
        "last_webhook_at",
        "last_magic_link_at",
    }
    assert email not in response.text

    subscription_response = client.get(
        f"/api/v1/internal/support/watchers/{payload['watcher_id']}/subscription",
        headers=_support_headers(token, request_id="req-support-subscription"),
    )
    assert subscription_response.status_code == 200
    subscription_payload = subscription_response.json()
    assert subscription_payload["subscription_state"] == "active"
    assert subscription_payload["subscription_id_masked"] != subscription_id
    assert "sub_support_001" not in subscription_response.text

    webhooks_response = client.get(
        f"/api/v1/internal/support/watchers/{payload['watcher_id']}/webhooks/latest?limit=5",
        headers=_support_headers(token, request_id="req-support-webhooks"),
    )
    assert webhooks_response.status_code == 200
    webhooks_payload = webhooks_response.json()
    assert webhooks_payload["items"]
    assert webhooks_payload["items"][0]["event_type"] == "order.created"
    assert webhooks_payload["items"][0]["delivery_status"] == "accepted"


def test_internal_support_resend_magic_link_updates_state_without_leaking_token(
    monkeypatch: pytest.MonkeyPatch,
    support_api_ctx: dict[str, Any],
) -> None:
    """Le renvoi de magic link audité n'expose jamais le token brut."""

    _FakeSMTP.instances.clear()
    monkeypatch.setattr("smtplib.SMTP", _FakeSMTP)

    app = support_api_ctx["app"]
    dataset_id = support_api_ctx["dataset_id"]
    secret = support_api_ctx["secret"]
    token = support_api_ctx["internal_token"]
    email = "resend-support@example.ch"
    subscription_id = "sub_resend_001"
    client = cast(_SupportHttpClient, TestClient(app))
    watcher_repo = SqlAlchemyWatcherRepository()

    create_response = _create_watcher_via_webhook(
        client, dataset_id, secret, email, subscription_id
    )
    assert create_response.status_code == 200

    watcher = watcher_repo.find_by_email(email)
    assert watcher is not None
    watcher_id = watcher.id
    magic_state_before = client.get(
        f"/api/v1/internal/support/watchers/{watcher_id}/magic-links/state",
        headers=_support_headers(token, request_id="req-support-magic-state-before"),
    )
    assert magic_state_before.status_code == 200
    assert magic_state_before.json()["active_unexpired_count"] == 1

    resend_response = client.post(
        f"/api/v1/internal/support/watchers/{watcher_id}/magic-link/resend",
        headers={
            **_support_headers(token, request_id="req-support-resend"),
            "Content-Type": "application/json",
        },
        json={"reason": "incident_paid_no_access"},
    )

    assert resend_response.status_code == 200
    resend_payload = resend_response.json()
    assert resend_payload["dispatch_status"] == "sent"
    assert "token" not in resend_response.text
    assert resend_payload["audit_id"]

    magic_state_after = client.get(
        f"/api/v1/internal/support/watchers/{watcher_id}/magic-links/state",
        headers=_support_headers(token, request_id="req-support-magic-state-after"),
    )
    assert magic_state_after.status_code == 200
    assert magic_state_after.json()["active_unexpired_count"] == 2

    deliverability_response = client.get(
        f"/api/v1/internal/support/watchers/{watcher_id}/email-deliverability",
        headers=_support_headers(token, request_id="req-support-deliverability"),
    )
    assert deliverability_response.status_code == 200
    deliverability_payload = deliverability_response.json()
    assert deliverability_payload["last_send_status"] == "sent"
    assert deliverability_payload["recent_error_count_24h"] == 0
    assert deliverability_payload["last_send_at"] is not None

    assert _FakeSMTP.instances
    assert _FakeSMTP.instances[0].started_tls is True
    assert _FakeSMTP.instances[0].logged_in is True
    assert _FakeSMTP.instances[0].sent_messages


def test_internal_support_rejects_invalid_auth_and_suspended_resend(
    support_api_ctx: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Le support interne rejette l'auth invalide et refuse le renvoi si suspendu."""

    app = support_api_ctx["app"]
    dataset_id = support_api_ctx["dataset_id"]
    secret = support_api_ctx["secret"]
    token = support_api_ctx["internal_token"]
    email = "blocked-support@example.ch"
    subscription_id = "sub_blocked_001"
    client = cast(_SupportHttpClient, TestClient(app))
    watcher_repo = SqlAlchemyWatcherRepository()

    create_response = _create_watcher_via_webhook(
        client, dataset_id, secret, email, subscription_id
    )
    assert create_response.status_code == 200
    watcher = watcher_repo.find_by_email(email)
    assert watcher is not None
    watcher_id = watcher.id

    unauthorized_response = client.get(
        f"/api/v1/internal/support/watchers/by-email?email={email}",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert unauthorized_response.status_code == 401
    assert token not in caplog.text

    cancel_response = _cancel_subscription_webhook(client, secret, subscription_id)
    assert cancel_response.status_code == 200

    suspended_resend_response = client.post(
        f"/api/v1/internal/support/watchers/{watcher_id}/magic-link/resend",
        headers={
            **_support_headers(token, request_id="req-support-suspended"),
            "Content-Type": "application/json",
        },
        json={"reason": "incident_paid_no_access"},
    )
    assert suspended_resend_response.status_code == 409
