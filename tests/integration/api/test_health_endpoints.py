"""Tests d'integration du contrat de lecture minimal API."""

from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.ckan_normalized import Dataset, NormalizedBatch, Organization, Resource


def _configure_api_modules():
    """Recharge les modules relies a la DB pour les tests de lecture API."""

    import app.core.config as config_module

    config_module.get_settings.cache_clear()

    import app.application.use_cases.get_health_status as health_use_case_module
    import app.infrastructure.persistence.cache_read_repository as cache_read_repository_module
    import app.infrastructure.persistence.cache_repository as cache_repository_module
    import app.infrastructure.persistence.database as database_module
    import app.infrastructure.persistence.models as models_module
    import app.main as main_module
    import app.presentation.api.v1.router as router_module

    database_module = importlib.reload(database_module)
    models_module = importlib.reload(models_module)
    cache_repository_module = importlib.reload(cache_repository_module)
    cache_read_repository_module = importlib.reload(cache_read_repository_module)
    health_use_case_module = importlib.reload(health_use_case_module)
    router_module = importlib.reload(router_module)
    main_module = importlib.reload(main_module)

    return database_module, cache_repository_module, main_module


def test_health_and_internal_cache_with_empty_cache(monkeypatch, tmp_path: Path) -> None:
    """Expose un service ok avec cache vide et sans dernier sync."""

    database_path = tmp_path / "health-empty.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_module, _, main_module = _configure_api_modules()
    database_module.create_schema()

    client = TestClient(main_module.app)

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


def test_health_and_internal_cache_with_populated_cache(monkeypatch, tmp_path: Path) -> None:
    """Expose le dernier sync et les compteurs quand le cache est peuple."""

    database_path = tmp_path / "health-populated.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_module, cache_repository_module, main_module = _configure_api_modules()
    database_module.create_schema()

    repository = cache_repository_module.SqlAlchemyCacheRepository()
    repository.upsert_normalized_batch(
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

    client = TestClient(main_module.app)

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
