"""Tests d'integration du contrat de lecture minimal API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domain.ckan_normalized import Dataset, NormalizedBatch, Organization, Resource

from ._fixtures import configure_api_modules


def test_health_and_internal_cache_with_empty_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Expose un service ok avec cache vide et sans dernier sync."""

    database_path = tmp_path / "health-empty.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, _, app = configure_api_modules()
    database_port.create_schema()

    client = TestClient(app)

    health_response = client.get("/api/v1/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok", "last_sync": None}

    internal_response = client.get("/api/v1/internal/cache")
    assert internal_response.status_code == 200
    assert internal_response.json() == {
        "status": "ok",
        "last_sync": None,
        "cache_populated": False,
        "counts": {
            "organizations": 0,
            "datasets": 0,
            "resources": 0,
        },
    }


def test_health_and_internal_cache_with_populated_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Expose le dernier sync et les compteurs quand le cache est peuple."""

    database_path = tmp_path / "health-populated.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()

    cache_repository.upsert_normalized_batch(
        NormalizedBatch(
            organizations=[
                Organization(
                    id="org-1",
                    name="Organisation Test",
                    last_synced="2026-06-13T10:30:00+00:00",
                )
            ],
            datasets=[
                Dataset(
                    id="dataset-1",
                    org_id="org-1",
                    title="Dataset Test",
                    normalized_at="2026-06-13T10:30:00+00:00",
                )
            ],
            resources=[
                Resource(
                    id="resource-1",
                    dataset_id="dataset-1",
                    name="Ressource Test",
                )
            ],
        )
    )

    client = TestClient(app)

    health_response = client.get("/api/v1/health")
    assert health_response.status_code == 200
    assert health_response.json() == {
        "status": "ok",
        "last_sync": "2026-06-13T10:30:00+00:00",
    }

    internal_response = client.get("/api/v1/internal/cache")
    assert internal_response.status_code == 200
    assert internal_response.json() == {
        "status": "ok",
        "last_sync": "2026-06-13T10:30:00+00:00",
        "cache_populated": True,
        "counts": {
            "organizations": 1,
            "datasets": 1,
            "resources": 1,
        },
    }
