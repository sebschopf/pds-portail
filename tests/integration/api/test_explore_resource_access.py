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


def test_explore_resource_quota_consumed_only_on_cache_miss(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    test_csv_resource: str,
    api_key: str,
) -> None:
    """PDS-109: Quota consommé seulement sur cache miss, pas sur cache hit.

    Scenario:
    1. Premier appel (cache miss) → quota 0→1
    2. Deuxième appel (cache hit, TTL 24h) → quota reste 1
    3. Troisième appel (cache hit) → quota reste 1
    """

    assert valid_license is not None
    client = cast(Any, TestClient(app_with_temp_db))

    # Etat initial : quota = 0
    session = SessionLocal()
    try:
        lic = session.query(LicenseModel).filter_by(id="test-license").first()
        assert lic is not None
        assert lic.used_this_month == 0
    finally:
        session.close()

    # Premier appel : cache miss → quota 0→1
    response1 = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": api_key},
        ),
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1.get("cached") is False  # Cache miss

    session = SessionLocal()
    try:
        lic = session.query(LicenseModel).filter_by(id="test-license").first()
        assert lic is not None
        assert lic.used_this_month == 1  # Quota consommé
    finally:
        session.close()

    # Deuxième appel : cache hit → quota reste 1
    response2 = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": api_key},
        ),
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2.get("cached") is True  # Cache hit

    session = SessionLocal()
    try:
        lic = session.query(LicenseModel).filter_by(id="test-license").first()
        assert lic is not None
        assert lic.used_this_month == 1  # Quota PAS consommé (cache hit)
    finally:
        session.close()

    # Troisième appel : cache hit → quota reste 1
    response3 = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": api_key},
        ),
    )
    assert response3.status_code == 200
    data3 = response3.json()
    assert data3.get("cached") is True  # Cache hit

    session = SessionLocal()
    try:
        lic = session.query(LicenseModel).filter_by(id="test-license").first()
        assert lic is not None
        assert lic.used_this_month == 1  # Quota PAS consommé (cache hit)
    finally:
        session.close()


def test_explore_resource_unreachable_url_returns_422(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    api_key: str,
) -> None:
    """POST /resources/{id}/explore URL inaccessible → 422 explicite (pas 500).

    PDS-109: Aucun quota consommé en cas d'erreur fetch.
    """

    assert valid_license is not None
    _, cache_repository, _ = configure_api_modules()

    org = Organization(
        id="org-unreachable",
        name="Test",
        description="Test",
        last_synced="2026-07-02T00:00:00Z",
    )
    dataset = Dataset(
        id="ds-unreachable",
        org_id="org-unreachable",
        title="Dataset unreachable",
        created="2026-07-02T00:00:00Z",
    )
    resource = Resource(
        id="res-unreachable",
        dataset_id="ds-unreachable",
        name="Resource unreachable",
        format="CSV",
        # Port 1 est invalide localement, provoque une erreur d'acces deterministic.
        url="http://127.0.0.1:1/unreachable.csv",
    )
    cache_repository.upsert_normalized_batch(NormalizedBatch([org], [dataset], [resource]))

    client = cast(Any, TestClient(app_with_temp_db))

    # Etat initial
    session = SessionLocal()
    try:
        lic = session.query(LicenseModel).filter_by(id="test-license").first()
        assert lic is not None
        initial_usage = lic.used_this_month
    finally:
        session.close()

    # Appel qui provoque une erreur fetch
    response = cast(
        Response,
        client.post(
            "/api/v1/resources/res-unreachable/explore",
            headers={"X-API-Key": api_key},
        ),
    )

    assert response.status_code == 422
    assert "inaccessible" in response.json()["detail"].lower()

    # Vérifier que le quota N'a PAS été consommé (PDS-109)
    session = SessionLocal()
    try:
        lic = session.query(LicenseModel).filter_by(id="test-license").first()
        assert lic is not None
        assert lic.used_this_month == initial_usage  # Pas de consommation
    finally:
        session.close()
