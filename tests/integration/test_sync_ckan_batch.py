"""Tests d'integration du vertical slice d'ingestion CKAN."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import select

from app.application.errors.ingestion import CkanRateLimitError, CkanTimeoutError
from app.application.ports.ckan_payloads import parse_package_search_response
from app.application.ports.ckan_types import CkanPackageSearchResponse


class FakeCkanClient:
    """Client CKAN factice qui memorise les appels de pagination."""

    def __init__(self, payloads: list[CkanPackageSearchResponse]) -> None:
        self._payloads = payloads
        self._cursor = 0
        self.calls: list[tuple[int, int]] = []

    def fetch_packages_batch(
        self, start: int, rows: int = 100, modified_since: str | None = None
    ) -> CkanPackageSearchResponse:
        self.calls.append((start, rows))
        _ = modified_since
        payload = self._payloads[min(self._cursor, len(self._payloads) - 1)]
        self._cursor += 1
        return payload


class FaultyCkanClient:
    """Client CKAN factice qui leve des erreurs pour tester la resilience."""

    def __init__(self, error: type[Exception]) -> None:
        self._error = error
        self.calls: list[tuple[int, int]] = []

    def fetch_packages_batch(
        self, start: int, rows: int = 100, modified_since: str | None = None
    ) -> CkanPackageSearchResponse:
        self.calls.append((start, rows))
        _ = (start, rows, modified_since)
        raise self._error("Simulee")


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


def test_sync_ckan_batch_normalizes_and_deduplicates_multilingual_tags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Les tags multilingues sont parses puis normalises sans doublons semantiques."""

    database_path = tmp_path / "sync-tags-normalized.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_module, models_module, repository_module, use_case_module = _configure_test_modules()
    database_module.create_schema()

    raw_payload: dict[str, object] = {
        "result": {
            "results": [
                {
                    "id": "dataset-tags-001",
                    "title": "Dataset tags",
                    "notes": "Validation tags",
                    "metadata_created": "2026-06-01T08:00:00Z",
                    "organization": {
                        "id": "org-tags-001",
                        "name": "org-tags",
                    },
                    "tags": [
                        {"display_name": {"fr": "Mobilite"}},
                        {"display_name": {"en": "Mobilité"}},
                        {"name": "  MOBILITE  "},
                        {"name": "Open Data"},
                    ],
                    "resources": [],
                }
            ]
        }
    }
    payload = parse_package_search_response(raw_payload)

    client = FakeCkanClient([payload])
    repository = repository_module.SqlAlchemyCacheRepository()
    use_case = use_case_module.SyncCkanBatchUseCase(client=client, repository=repository)
    use_case.execute(start=0, rows=100)

    with database_module.SessionLocal() as session:
        dataset = session.scalar(
            select(models_module.DatasetModel).where(
                models_module.DatasetModel.id == "dataset-tags-001"
            )
        )

    assert dataset is not None
    assert dataset.tags is not None
    parsed_tags = json.loads(dataset.tags)
    assert parsed_tags == ["mobilite", "open data"]


def test_normalizer_parametrable_par_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Une source fictive peut etre branchee avec son propre normalisateur (PDS-126 AC#3)."""

    database_path = tmp_path / "sync-source-fictive.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_module, models_module, repository_module, use_case_module = _configure_test_modules()
    database_module.create_schema()

    payload = _package_payload("Données source fictive", "Export JSON")

    # Normalisateur factice : même logique CKAN mais avec source="fictive-src"
    from app.domain.ckan_normalizer import CkanNormalizer

    fake_normalizer = CkanNormalizer(source="fictive-src")

    client = FakeCkanClient([payload])
    repository = repository_module.SqlAlchemyCacheRepository()
    use_case = use_case_module.SyncCkanBatchUseCase(
        client=client,
        repository=repository,
        normalizer=fake_normalizer,
    )

    batch = use_case.execute(start=0, rows=100)

    assert len(batch.datasets) == 1
    assert batch.datasets[0].source == "fictive-src"
    assert len(batch.organizations) == 1
    assert batch.organizations[0].source == "fictive-src"
    assert len(batch.resources) == 2
    assert all(r.source == "fictive-src" for r in batch.resources)

    # Vérification en base
    with database_module.SessionLocal() as session:
        db_dataset = session.scalar(
            select(models_module.DatasetModel).where(models_module.DatasetModel.id == "dataset-001")
        )
        db_org = session.scalar(
            select(models_module.OrganizationModel).where(
                models_module.OrganizationModel.id == "org-001"
            )
        )
        db_resources = session.scalars(
            select(models_module.ResourceModel).where(
                models_module.ResourceModel.dataset_id == "dataset-001"
            )
        ).all()

    assert db_dataset is not None
    assert db_dataset.source == "fictive-src"
    assert db_org is not None
    assert db_org.source == "fictive-src"
    assert len(db_resources) == 2
    assert all(r.source == "fictive-src" for r in db_resources)


def test_execute_resiste_timeout_et_retourne_batch_vide(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Un timeout CKAN est intercepté et retourne un batch vide (lignes 66-68)."""

    database_path = tmp_path / "sync-timeout.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_module, _models_module, repository_module, use_case_module = _configure_test_modules()
    database_module.create_schema()

    client = FaultyCkanClient(CkanTimeoutError)
    repository = repository_module.SqlAlchemyCacheRepository()
    use_case = use_case_module.SyncCkanBatchUseCase(client=client, repository=repository)

    batch = use_case.execute(start=0, rows=100)

    assert client.calls == [(0, 100)]
    assert len(batch.datasets) == 0
    assert len(batch.organizations) == 0
    assert len(batch.resources) == 0


def test_execute_resiste_rate_limit_et_retourne_batch_vide(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Un rate-limit CKAN est intercepté et retourne un batch vide (lignes 69-73)."""

    database_path = tmp_path / "sync-ratelimit.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_module, _models_module, repository_module, use_case_module = _configure_test_modules()
    database_module.create_schema()

    client = FaultyCkanClient(CkanRateLimitError)
    repository = repository_module.SqlAlchemyCacheRepository()
    use_case = use_case_module.SyncCkanBatchUseCase(client=client, repository=repository)

    batch = use_case.execute(start=0, rows=100)

    assert client.calls == [(0, 100)]
    assert len(batch.datasets) == 0
    assert len(batch.organizations) == 0
    assert len(batch.resources) == 0


def test_execute_rejette_rows_invalide(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """rows <= 0 leve ValueError (ligne 55)."""

    database_path = tmp_path / "sync-val.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_module, _models_module, repository_module, use_case_module = _configure_test_modules()
    database_module.create_schema()

    client = FakeCkanClient([])
    repository = repository_module.SqlAlchemyCacheRepository()
    use_case = use_case_module.SyncCkanBatchUseCase(client=client, repository=repository)

    with pytest.raises(ValueError, match="rows doit etre > 0"):
        use_case.execute(start=0, rows=0)

    with pytest.raises(ValueError, match="rows doit etre > 0"):
        use_case.execute(start=0, rows=-5)


def test_execute_rejette_start_negatif(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """start < 0 leve ValueError (ligne 57)."""

    database_path = tmp_path / "sync-val2.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_module, _models_module, repository_module, use_case_module = _configure_test_modules()
    database_module.create_schema()

    client = FakeCkanClient([])
    repository = repository_module.SqlAlchemyCacheRepository()
    use_case = use_case_module.SyncCkanBatchUseCase(client=client, repository=repository)

    with pytest.raises(ValueError, match="start doit etre >= 0"):
        use_case.execute(start=-1, rows=100)
