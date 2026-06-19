"""Tests d'integration du vertical slice d'ingestion CKAN."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import select

from app.application.ports.ckan_types import CkanPackageSearchResponse


class FakeCkanClient:
    """Client CKAN factice qui memorise les appels de pagination."""

    def __init__(self, payloads: list[CkanPackageSearchResponse]) -> None:
        self._payloads = payloads
        self._cursor = 0
        self.calls: list[tuple[int, int]] = []

    def fetch_packages_batch(self, start: int, rows: int = 100) -> CkanPackageSearchResponse:
        self.calls.append((start, rows))
        payload = self._payloads[min(self._cursor, len(self._payloads) - 1)]
        self._cursor += 1
        return payload


def _package_payload(title: str, resource_name: str) -> CkanPackageSearchResponse:
    """Construit un payload CKAN minimal mais representatif pour le test."""

    return {
        "result": {
            "results": [
                {
                    "id": "dataset-001",
                    "title": title,
                    "notes": "Donnees de mobilite urbaines",
                    "metadata_created": "2026-06-01T08:00:00Z",
                    "metadata_modified": "2026-06-13T09:30:00Z",
                    "url": "https://opendata.example/datasets/dataset-001",
                    "organization": {
                        "id": "org-001",
                        "name": "mobilite-ville",
                        "title": "Mobilite Ville",
                        "description": "Organisation de test",
                        "url": "https://opendata.example/orgs/org-001",
                    },
                    "tags": [
                        {"name": "mobilite"},
                        {"name": "geospatial"},
                        {"display_name": "tram"},
                    ],
                    "resources": [
                        {
                            "id": "resource-001",
                            "name": resource_name,
                            "format": "CSV",
                            "url": "https://opendata.example/resources/resource-001.csv",
                            "size": 2048,
                            "created": "2026-06-01T08:00:00Z",
                            "last_modified": "2026-06-13T09:30:00Z",
                        },
                        {
                            "id": "resource-002",
                            "description": "Documentation PDF",
                            "format": "PDF",
                            "url": "https://opendata.example/resources/resource-002.pdf",
                            "size": 1024,
                            "created": "2026-06-01T08:00:00Z",
                            "last_modified": "2026-06-13T09:30:00Z",
                        },
                    ],
                }
            ]
        }
    }


def _configure_test_modules() -> tuple[ModuleType, ModuleType, ModuleType, ModuleType]:
    """Recharge les modules relies a la base pour viser une SQLite temporaire."""

    import app.core.config as config_module

    config_module.get_settings.cache_clear()

    import app.application.use_cases.sync_ckan_batch as use_case_module
    import app.infrastructure.persistence.cache_repository as repository_module
    import app.infrastructure.persistence.database as database_module
    import app.infrastructure.persistence.models as models_module

    database_module = importlib.reload(database_module)
    models_module = importlib.reload(models_module)
    repository_module = importlib.reload(repository_module)
    use_case_module = importlib.reload(use_case_module)

    return database_module, models_module, repository_module, use_case_module


def test_sync_ckan_batch_is_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Valide pagination a 100, upsert des entites et absence de doublons."""

    database_path = tmp_path / "sync-validation.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_module, models_module, repository_module, use_case_module = _configure_test_modules()
    database_module.create_schema()

    client = FakeCkanClient(
        [
            _package_payload("Jeu de donnees mobilite", "Horaires tram CSV"),
            _package_payload("Jeu de donnees mobilite mis a jour", "Horaires tram CSV v2"),
        ]
    )
    repository = repository_module.SqlAlchemyCacheRepository()
    use_case = use_case_module.SyncCkanBatchUseCase(client=client, repository=repository)

    first_batch = use_case.execute(start=0, rows=100)
    second_batch = use_case.execute(start=0, rows=100)

    assert client.calls == [(0, 100), (0, 100)]
    assert len(first_batch.organizations) == 1
    assert len(first_batch.datasets) == 1
    assert len(first_batch.resources) == 2
    assert len(second_batch.datasets) == 1
    assert second_batch.datasets[0].quality_score == 90
    assert second_batch.datasets[0].completeness == 100
    assert second_batch.datasets[0].freshness_days is not None

    with database_module.SessionLocal() as session:
        organizations = session.scalars(select(models_module.OrganizationModel)).all()
        datasets = session.scalars(select(models_module.DatasetModel)).all()
        resources = session.scalars(select(models_module.ResourceModel)).all()

    assert len(organizations) == 1
    assert len(datasets) == 1
    assert len(resources) == 2
    assert datasets[0].title == "Jeu de donnees mobilite mis a jour"
    assert datasets[0].quality_score == 90
    assert datasets[0].completeness == 100
    assert datasets[0].freshness_days is not None
    assert resources[0].name in {"Horaires tram CSV v2", "Documentation PDF"}
    assert resources[1].name in {"Horaires tram CSV v2", "Documentation PDF"}
    assert {resource.id for resource in resources} == {"resource-001", "resource-002"}
