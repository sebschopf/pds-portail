"""Tests d'accès et de règles métier pour POST /resources/{id}/explore."""

from __future__ import annotations

from typing import Any, cast

from fastapi.testclient import TestClient
from httpx import Response

from app.domain.ckan_normalized import Dataset, NormalizedBatch, Organization, Resource
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import LicenseModel

from ._fixtures import configure_api_modules


def test_explore_resource_without_api_key(app_with_temp_db: Any) -> None:
    """POST /resources/{id}/explore sans X-API-Key → 401."""

    client = cast(Any, TestClient(app_with_temp_db))

    response = cast(Response, client.post("/api/v1/resources/any/explore"))

    assert response.status_code == 401
    assert "Missing X-API-Key" in response.json()["detail"]


def test_explore_resource_with_invalid_key(app_with_temp_db: Any) -> None:
    """POST /resources/{id}/explore avec clé invalide → 401."""

    client = cast(Any, TestClient(app_with_temp_db))

    response = cast(
        Response,
        client.post(
            "/api/v1/resources/any/explore",
            headers={"X-API-Key": "invalid-key-999"},
        ),
    )

    assert response.status_code == 401
    assert "Invalid or expired" in response.json()["detail"]


def test_explore_resource_not_found(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    api_key: str,
) -> None:
    """POST /resources/{id}/explore ressource inexistante → 404."""

    assert valid_license is not None
    client = cast(Any, TestClient(app_with_temp_db))

    response = cast(
        Response,
        client.post(
            "/api/v1/resources/nonexistent/explore",
            headers={"X-API-Key": api_key},
        ),
    )

    assert response.status_code == 404


def test_explore_resource_unsupported_format(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    api_key: str,
) -> None:
    """POST /resources/{id}/explore format PDF non supporté → 422."""

    assert valid_license is not None
    _, cache_repository, _ = configure_api_modules()

    org = Organization(
        id="org-1", name="Test", description="Test", last_synced="2026-07-02T00:00:00Z"
    )
    dataset = Dataset(id="ds-1", org_id="org-1", title="Test", created="2026-07-02T00:00:00Z")
    resource = Resource(
        id="res-pdf",
        dataset_id="ds-1",
        name="Data",
        format="PDF",
        url="http://x.com/data.pdf",
    )
    cache_repository.upsert_normalized_batch(NormalizedBatch([org], [dataset], [resource]))

    client = cast(Any, TestClient(app_with_temp_db))
    response = cast(
        Response,
        client.post(
            "/api/v1/resources/res-pdf/explore",
            headers={"X-API-Key": api_key},
        ),
    )

    assert response.status_code == 422


def test_explore_resource_increments_usage(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    test_csv_resource: str,
    api_key: str,
) -> None:
    """POST /resources/{id}/explore incrémente used_this_month (0→1→2)."""

    assert valid_license is not None
    client = cast(Any, TestClient(app_with_temp_db))

    session = SessionLocal()
    try:
        lic = session.query(LicenseModel).filter_by(id="test-license").first()
        assert lic is not None
        assert lic.used_this_month == 0
    finally:
        session.close()

    response1 = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": api_key},
        ),
    )
    assert response1.status_code == 200

    session = SessionLocal()
    try:
        lic = session.query(LicenseModel).filter_by(id="test-license").first()
        assert lic is not None
        assert lic.used_this_month == 1
    finally:
        session.close()

    response2 = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": api_key},
        ),
    )
    assert response2.status_code == 200

    session = SessionLocal()
    try:
        lic = session.query(LicenseModel).filter_by(id="test-license").first()
        assert lic is not None
        assert lic.used_this_month == 2
    finally:
        session.close()
