"""Tests d'integration des endpoints de recherche et detail dataset."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Protocol, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from app.domain.ckan_normalized import Dataset, NormalizedBatch, Organization, Resource


class DatabaseModulePort(Protocol):
    """Port minimal du module database pour les tests API."""

    def create_schema(self) -> None:
        """Cree le schema SQL local pour les tests."""


class CacheRepositoryPort(Protocol):
    """Port minimal du repository de cache pour injection de fixtures."""

    def upsert_normalized_batch(self, batch: NormalizedBatch) -> None:
        """Persiste un lot normalise dans le cache local."""


def _configure_api_modules() -> tuple[DatabaseModulePort, CacheRepositoryPort, FastAPI]:
    """Recharge les modules relies a la DB pour les tests de lecture API."""

    import app.core.config as config_module

    config_module.get_settings.cache_clear()

    import app.application.use_cases.get_dataset_detail as dataset_detail_use_case_module
    import app.application.use_cases.get_resource_detail as resource_detail_use_case_module
    import app.application.use_cases.search_datasets as search_datasets_use_case_module
    import app.infrastructure.persistence.cache_repository as cache_repository_module
    import app.infrastructure.persistence.database as database_module
    import app.infrastructure.persistence.models as models_module
    import app.infrastructure.persistence.search_repository as search_repository_module
    import app.main as main_module
    import app.presentation.api.v1.router as router_module

    database_module = importlib.reload(database_module)
    models_module = importlib.reload(models_module)
    cache_repository_module = importlib.reload(cache_repository_module)
    search_repository_module = importlib.reload(search_repository_module)
    search_datasets_use_case_module = importlib.reload(search_datasets_use_case_module)
    dataset_detail_use_case_module = importlib.reload(dataset_detail_use_case_module)
    resource_detail_use_case_module = importlib.reload(resource_detail_use_case_module)
    router_module = importlib.reload(router_module)
    main_module = importlib.reload(main_module)

    database_port = cast(DatabaseModulePort, database_module)
    cache_repository = cast(
        CacheRepositoryPort,
        cache_repository_module.SqlAlchemyCacheRepository(),
    )
    app: FastAPI = main_module.app

    return database_port, cache_repository, app


def _populate_cache_nominale(cache_repository: CacheRepositoryPort) -> tuple[str, str]:
    """Peuple le cache avec des donnees de test nominales.

    Returns:
        (dataset_id, resource_id) des elements inseres
    """

    org = Organization(
        id="org-001",
        name="Mobilite Urbaine",
        description="Donnees de mobilite",
        ckan_url="https://opendata.swiss/organization/mobilite",
        last_synced="2026-06-13T10:00:00Z",
    )

    resource = Resource(
        id="resource-001",
        dataset_id="dataset-001",
        name="Flux de mobilite CSV",
        format="CSV",
        url="https://opendata.swiss/dataset/mobilite/resource/resource-001/download",
        size_bytes=12345678,
        created="2026-01-01T08:00:00Z",
        last_modified="2026-06-10T15:30:00Z",
    )

    dataset = Dataset(
        id="dataset-001",
        org_id="org-001",
        title="Donnees de mobilite urbaine",
        description="Flux de mobilite collectes dans les zones urbaines, normalises et structures",
        tags=["mobilite", "transports", "urbain", "temps-reel"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=82,
        completeness=88,
        freshness_days=3,
        ckan_url="https://opendata.swiss/dataset/mobilite",
    )

    batch = NormalizedBatch(organizations=[org], datasets=[dataset], resources=[resource])
    cache_repository.upsert_normalized_batch(batch)

    return dataset.id, resource.id


def _populate_cache_facets(cache_repository: CacheRepositoryPort) -> None:
    """Peuple le cache avec 2 datasets pour verifier les facettes."""

    org = Organization(
        id="org-001",
        name="Mobilite Urbaine",
        description="Donnees de mobilite",
        ckan_url="https://opendata.swiss/organization/mobilite",
        last_synced="2026-06-13T10:00:00Z",
    )

    dataset_csv = Dataset(
        id="dataset-csv",
        org_id="org-001",
        title="Flux mobilite CSV",
        description="Jeu de donnees mobilite format CSV",
        tags=["mobilite", "open-data"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=80,
        completeness=85,
        freshness_days=4,
    )
    resource_csv = Resource(
        id="resource-csv",
        dataset_id="dataset-csv",
        name="Export CSV",
        format="CSV",
        url="https://example.org/csv",
    )

    dataset_json = Dataset(
        id="dataset-json",
        org_id="org-001",
        title="Flux mobilite JSON",
        description="Jeu de donnees mobilite format JSON",
        tags=["mobilite", "api"],
        created="2026-01-02T08:00:00Z",
        modified="2026-06-11T15:30:00Z",
        quality_score=81,
        completeness=86,
        freshness_days=3,
    )
    resource_json = Resource(
        id="resource-json",
        dataset_id="dataset-json",
        name="Export JSON",
        format="JSON",
        url="https://example.org/json",
    )

    batch = NormalizedBatch(
        organizations=[org],
        datasets=[dataset_csv, dataset_json],
        resources=[resource_csv, resource_json],
    )
    cache_repository.upsert_normalized_batch(batch)


def _populate_cache_organizations_many(cache_repository: CacheRepositoryPort) -> None:
    """Peuple >20 organisations pour verifier ordre deterministic + limite facette."""

    organizations: list[Organization] = []
    datasets: list[Dataset] = []
    resources: list[Resource] = []

    for i in range(25):
        org_id = f"org-{i:02d}"
        org_name = f"Org-{i:02d}"
        dataset_id = f"dataset-org-{i:02d}"
        resource_id = f"resource-org-{i:02d}"

        organizations.append(
            Organization(
                id=org_id,
                name=org_name,
                description=f"Organisation {i}",
                ckan_url=f"https://example.org/{org_id}",
                last_synced="2026-06-13T10:00:00Z",
            )
        )
        datasets.append(
            Dataset(
                id=dataset_id,
                org_id=org_id,
                title=f"Dataset {i:02d}",
                description="Dataset de test",
                tags=["test"],
                created="2026-01-01T08:00:00Z",
                modified="2026-06-10T15:30:00Z",
                quality_score=50,
                completeness=50,
                freshness_days=5,
            )
        )
        resources.append(
            Resource(
                id=resource_id,
                dataset_id=dataset_id,
                name=f"Ressource {i:02d}",
                format="CSV",
                url=f"https://example.org/{resource_id}",
            )
        )

    cache_repository.upsert_normalized_batch(
        NormalizedBatch(
            organizations=organizations,
            datasets=datasets,
            resources=resources,
        )
    )


def test_search_empty_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/search sur un cache vide retourne resultats vides."""

    database_path = tmp_path / "search-empty.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, _, app = _configure_api_modules()
    database_port.create_schema()

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/search"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["total"] == 0
    assert data["datasets"] == []
    assert data["offset"] == 0
    assert data["limit"] == 20


def test_search_nominale(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/search retourne les datasets avec pagination et facettes."""

    database_path = tmp_path / "search-nominale.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = _configure_api_modules()
    database_port.create_schema()

    dataset_id, _ = _populate_cache_nominale(cache_repository)

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/search"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["total"] == 1
    assert len(data["datasets"]) == 1

    datasets = cast(list[dict[str, Any]], data["datasets"])
    item = datasets[0]
    assert item["id"] == dataset_id
    assert item["title"] == "Donnees de mobilite urbaine"
    assert item["org_name"] == "Mobilite Urbaine"
    assert item["quality_score"] == 82
    assert item["completeness"] == 88
    assert item["freshness_days"] == 3
    assert "CSV" in item["resource_formats"]


def test_search_with_query_filter(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/search?q=mobilite filtre sur titre/description/tags."""

    database_path = tmp_path / "search-query.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = _configure_api_modules()
    database_port.create_schema()

    dataset_id, _ = _populate_cache_nominale(cache_repository)

    client = cast(Any, TestClient(app))

    # Recherche qui doit matcher
    response = cast(Response, client.get("/api/v1/search?q=mobilite"))
    assert response.status_code == 200
    data_ok = cast(dict[str, Any], response.json())
    assert data_ok["total"] == 1
    assert cast(list[dict[str, Any]], data_ok["datasets"])[0]["id"] == dataset_id

    # Recherche qui ne doit pas matcher
    response = cast(Response, client.get("/api/v1/search?q=energie"))
    assert response.status_code == 200
    data_ko = cast(dict[str, Any], response.json())
    assert data_ko["total"] == 0


def test_search_pagination(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/search?offset=10&limit=5 respecte la pagination."""

    database_path = tmp_path / "search-pagination.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = _configure_api_modules()
    database_port.create_schema()

    _populate_cache_nominale(cache_repository)

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/search?offset=0&limit=5"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["offset"] == 0
    assert data["limit"] == 5
    assert data["total"] >= 0


def test_search_facets_formats_tags_and_filter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """GET /api/v1/search expose facettes formats/tags et applique fmt au niveau SQL."""

    database_path = tmp_path / "search-facets.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = _configure_api_modules()
    database_port.create_schema()
    _populate_cache_facets(cache_repository)

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/search"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["total"] == 2

    facets = cast(dict[str, Any], data["facets"])
    formats = cast(list[dict[str, Any]], facets["formats"])
    tags = cast(list[dict[str, Any]], facets["tags"])

    format_counts = {str(item["name"]): int(item["count"]) for item in formats}
    assert format_counts.get("CSV") == 1
    assert format_counts.get("JSON") == 1

    tag_counts = {str(item["name"]): int(item["count"]) for item in tags}
    assert tag_counts.get("mobilite") == 2
    assert tag_counts.get("open-data") == 1
    assert tag_counts.get("api") == 1

    filtered_response = cast(Response, client.get("/api/v1/search?fmt=CSV"))
    assert filtered_response.status_code == 200
    filtered_data = cast(dict[str, Any], filtered_response.json())
    assert filtered_data["total"] == 1
    assert len(cast(list[dict[str, Any]], filtered_data["datasets"])) == 1


def test_search_sort_explicit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/search?sort=... applique un tri explicite stable."""

    database_path = tmp_path / "search-sort.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = _configure_api_modules()
    database_port.create_schema()
    _populate_cache_facets(cache_repository)

    client = cast(Any, TestClient(app))

    by_modified_asc = cast(Response, client.get("/api/v1/search?sort=modified_asc"))
    assert by_modified_asc.status_code == 200
    by_modified_asc_data = cast(dict[str, Any], by_modified_asc.json())
    by_modified_asc_ids = [
        str(item["id"]) for item in cast(list[dict[str, Any]], by_modified_asc_data["datasets"])
    ]
    assert by_modified_asc_ids == ["dataset-csv", "dataset-json"]

    by_quality_desc = cast(Response, client.get("/api/v1/search?sort=quality_desc"))
    assert by_quality_desc.status_code == 200
    by_quality_desc_data = cast(dict[str, Any], by_quality_desc.json())
    by_quality_desc_ids = [
        str(item["id"]) for item in cast(list[dict[str, Any]], by_quality_desc_data["datasets"])
    ]
    assert by_quality_desc_ids == ["dataset-json", "dataset-csv"]


def test_search_sort_hybrid_exposes_ranking_signals(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """GET /api/v1/search?sort=hybrid active le ranking hybride et expose ses signaux."""

    database_path = tmp_path / "search-sort-hybrid.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = _configure_api_modules()
    database_port.create_schema()
    _populate_cache_facets(cache_repository)

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/search?q=mobilite&sort=hybrid"))
    assert response.status_code == 200

    data = cast(dict[str, Any], response.json())
    datasets = cast(list[dict[str, Any]], data["datasets"])

    assert [str(item["id"]) for item in datasets] == ["dataset-json", "dataset-csv"]
    assert datasets[0]["ranking_signals"] is not None
    assert datasets[1]["ranking_signals"] is not None
    assert (
        datasets[0]["ranking_signals"]["hybrid_score"]
        >= datasets[1]["ranking_signals"]["hybrid_score"]
    )


def test_search_sort_invalid_returns_422(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/search avec sort invalide retourne 422."""

    database_path = tmp_path / "search-sort-invalid.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, _, app = _configure_api_modules()
    database_port.create_schema()

    client = cast(Any, TestClient(app))
    response = cast(Response, client.get("/api/v1/search?sort=unknown_sort"))
    assert response.status_code == 422


def test_search_organization_facets_are_ordered_and_limited(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Facette organizations: ordre deterministic et limite fixe."""

    database_path = tmp_path / "search-org-facets.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = _configure_api_modules()
    database_port.create_schema()
    _populate_cache_organizations_many(cache_repository)

    client = cast(Any, TestClient(app))
    response = cast(Response, client.get("/api/v1/search"))
    assert response.status_code == 200

    data = cast(dict[str, Any], response.json())
    facets = cast(dict[str, Any], data["facets"])
    organizations = cast(list[dict[str, Any]], facets["organizations"])

    assert len(organizations) == 20
    ids = [str(item["name"]) for item in organizations]
    labels = [str(item["display_name"]) for item in organizations]
    assert ids == [f"org-{i:02d}" for i in range(20)]
    assert labels == [f"Org-{i:02d}" for i in range(20)]


def test_dataset_detail_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/dataset/{id} retourne 404 si dataset inexistant."""

    database_path = tmp_path / "detail-404.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, _, app = _configure_api_modules()
    database_port.create_schema()

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/dataset/nonexistent"))
    assert response.status_code == 404


def test_dataset_detail_nominale(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/dataset/{id} retourne le detail complet avec ressources."""

    database_path = tmp_path / "detail-nominale.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = _configure_api_modules()
    database_port.create_schema()

    dataset_id, resource_id = _populate_cache_nominale(cache_repository)

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get(f"/api/v1/dataset/{dataset_id}"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["id"] == dataset_id
    assert data["title"] == "Donnees de mobilite urbaine"
    assert data["quality_score"] == 82
    assert data["completeness"] == 88
    assert data["freshness_days"] == 3
    assert len(data["resources"]) == 1
    assert data["resources"][0]["id"] == resource_id
    assert data["resources"][0]["format"] == "CSV"
    assert len(data["access_modes"]) > 0


def test_resource_detail_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/resource/{id} retourne 404 si ressource inexistante."""

    database_path = tmp_path / "resource-404.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, _, app = _configure_api_modules()
    database_port.create_schema()

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/resource/nonexistent"))
    assert response.status_code == 404


def test_resource_detail_nominale(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/resource/{id} retourne le detail avec reference au dataset."""

    database_path = tmp_path / "resource-nominale.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = _configure_api_modules()
    database_port.create_schema()

    dataset_id, resource_id = _populate_cache_nominale(cache_repository)

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get(f"/api/v1/resource/{resource_id}"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["id"] == resource_id
    assert data["name"] == "Flux de mobilite CSV"
    assert data["format"] == "CSV"
    assert data["dataset_id"] == dataset_id
    assert data["dataset_title"] == "Donnees de mobilite urbaine"
