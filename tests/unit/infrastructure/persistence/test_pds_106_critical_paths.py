"""Tests de couverture des chemins critiques PDS-106."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

import app.core.config as config_module
import app.infrastructure.persistence.cache_repository as cache_repository_module
import app.infrastructure.persistence.compare_adapter as compare_adapter_module
import app.infrastructure.persistence.database as database_module
from app.domain.ckan_normalized import NormalizedBatch, Organization
from app.infrastructure.persistence._search_helpers import parse_tags
from app.infrastructure.persistence.cache_repository import SqlAlchemyCacheRepository
from app.infrastructure.persistence.compare_adapter import SqlAlchemyCompareAdapter
from app.infrastructure.persistence.models import DatasetModel, OrganizationModel, ResourceModel


@pytest.fixture
def isolated_sqlite_db(tmp_path: Path) -> Generator[None, None, None]:
    """Reconfigure la base vers une SQLite temporaire et restaure l'etat ensuite."""

    original_database_url = config_module.get_settings().database_url
    database_url = f"sqlite:///{tmp_path / 'pds106.db'}"

    database_module.reconfigure_for_test(database_url)
    database_module.create_schema()

    yield

    database_module.reconfigure_for_test(original_database_url)
    config_module.get_settings.cache_clear()


class _FakeScalarResult:
    def __init__(self, datasets: list[DatasetModel]) -> None:
        self._datasets = datasets

    def unique(self) -> _FakeScalarResult:
        return self

    def all(self) -> list[DatasetModel]:
        return self._datasets


class _FakeSession:
    def __init__(self, datasets: list[DatasetModel]) -> None:
        self._datasets = datasets

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *_exc_info: object) -> Any:
        return None

    def scalars(self, _query: object) -> _FakeScalarResult:
        return _FakeScalarResult(self._datasets)


def _build_compare_datasets() -> list[DatasetModel]:
    """Construit les objets ORM utilises pour simuler la couche DB compare."""

    organization = OrganizationModel(
        id="org-001",
        name="Organisation test",
        description="Organisation visible",
        ckan_url="https://example.test/org-001",
        last_synced=None,
        source="ckan",
    )

    dataset_with_org = DatasetModel(
        id="dataset-001",
        org_id="org-001",
        title="Dataset avec organisation",
        description="Visible et complet",
        tags='["mobilite", "transport"]',
        created=None,
        modified=None,
        quality_score=80,
        completeness=90,
        freshness_days=12,
        ckan_url="https://example.test/dataset-001",
        normalized_at=None,
        source="ckan",
    )
    dataset_with_org.organization = organization
    dataset_with_org.resources = [
        ResourceModel(
            id="resource-001",
            dataset_id="dataset-001",
            name="Ressource CSV",
            format="csv",
            url="https://example.test/resource-001.csv",
            size_bytes=128,
            created=None,
            last_modified=None,
            source="ckan",
        )
    ]

    dataset_without_org = DatasetModel(
        id="dataset-002",
        org_id="ghost-org",
        title="Dataset sans organisation",
        description="Organisation absente",
        tags="mobilite, transport",
        created=None,
        modified=None,
        quality_score=70,
        completeness=60,
        freshness_days=20,
        ckan_url="https://example.test/dataset-002",
        normalized_at=None,
        source="ckan",
    )
    dataset_without_org.resources = []

    return [dataset_with_org, dataset_without_org]


def test_compare_adapter_preserves_order_and_handles_missing_org(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le repo compare garde l'ordre demande, ignore les manquants et tolere org absente."""

    monkeypatch.setattr(
        compare_adapter_module,
        "SessionLocal",
        lambda: _FakeSession(_build_compare_datasets()),
    )

    adapter = SqlAlchemyCompareAdapter()
    items = adapter.get_by_ids(["dataset-002", "missing", "dataset-001"])

    assert [item.id for item in items] == ["dataset-002", "dataset-001"]
    assert items[0].org_name is None
    assert items[1].org_name == "Organisation test"
    assert items[1].resource_count == 1
    assert items[1].resource_formats == ["csv"]


def test_compare_adapter_returns_empty_list_for_empty_input() -> None:
    """Une requete vide retourne une liste vide sans toucher la base."""

    adapter = SqlAlchemyCompareAdapter()

    assert adapter.get_by_ids([]) == []


def test_parse_tags_supports_csv_and_valid_json() -> None:
    """Le helper parse les tags CSV et JSON sans garder les blancs."""

    assert parse_tags("mobilite, transport, , urbain") == ["mobilite", "transport", "urbain"]
    assert parse_tags('["mobilite", "transport", " "]') == ["mobilite", "transport"]


def test_parse_tags_returns_empty_list_for_invalid_json() -> None:
    """Un JSON invalide est ignore plutot que de casser le flux."""

    assert parse_tags('["mobilite",') == []


@pytest.mark.usefixtures("isolated_sqlite_db")
def test_cache_repository_upsert_recovers_from_ckan_url_conflict() -> None:
    """Le conflit ckan_url met a jour l'organisation existante au lieu de dupliquer."""

    with database_module.SessionLocal() as session:
        session.add(
            OrganizationModel(
                id="org-existing",
                name="Ancienne organisation",
                description="Ancienne description",
                ckan_url="https://example.test/org-conflict",
                last_synced="2026-06-30T00:00:00+00:00",
                source="legacy",
            )
        )
        session.commit()

    repository = SqlAlchemyCacheRepository()
    repository.upsert_normalized_batch(
        NormalizedBatch(
            organizations=[
                Organization(
                    id="org-new",
                    name="Organisation mise a jour",
                    description="Description actualisee",
                    ckan_url="https://example.test/org-conflict",
                    last_synced="2026-07-02T10:30:00+00:00",
                    source="ckan",
                )
            ],
            datasets=[],
            resources=[],
        )
    )

    with database_module.SessionLocal() as session:
        row = session.scalar(
            select(OrganizationModel).where(
                OrganizationModel.ckan_url == "https://example.test/org-conflict"
            )
        )

    assert row is not None
    assert row.id == "org-existing"
    assert row.name == "Organisation mise a jour"
    assert row.description == "Description actualisee"
    assert row.last_synced == "2026-07-02T10:30:00+00:00"
    assert row.source == "ckan"


def test_cache_repository_reraises_integrity_error_when_no_existing_org_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si la recherche de fallback ne trouve rien, l'IntegrityError remonte."""

    class _FakeQuery:
        def filter(self, *_args: object, **_kwargs: object) -> _FakeQuery:
            return self

        def first(self) -> None:
            return None

    class _FakeSession:
        def __enter__(self) -> Any:
            return self

        def __exit__(self, *_exc_info: object) -> None:
            return None

        def execute(self, _stmt: object) -> None:
            raise IntegrityError("stmt", {}, Exception("boom"))

        def query(self, _model: object) -> _FakeQuery:
            return _FakeQuery()

    monkeypatch.setattr(cache_repository_module, "SessionLocal", lambda: _FakeSession())

    repository = SqlAlchemyCacheRepository()

    with pytest.raises(IntegrityError):
        repository.upsert_normalized_batch(
            NormalizedBatch(
                organizations=[
                    Organization(
                        id="org-missing",
                        name="Organisation manquante",
                        ckan_url="https://example.test/org-missing",
                    )
                ],
                datasets=[],
                resources=[],
            )
        )
