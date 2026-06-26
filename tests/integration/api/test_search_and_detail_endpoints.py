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


def _configure_api_modules(
    enable_query_cache: bool = False,
) -> tuple[DatabaseModulePort, CacheRepositoryPort, FastAPI]:
    """Recharge les modules relies a la DB pour les tests de lecture API.

    Par defaut, le cache applicatif PDS-46 est desactive pour eviter de
    polluer les assertions existantes. Les tests specifiques au cache
    passent ``enable_query_cache=True``.
    """

    import os

    import app.core.config as config_module

    config_module.get_settings.cache_clear()

    # Desactiver le cache applicatif PDS-46 pour les tests existants
    if not enable_query_cache:
        os.environ["QUERY_CACHE_ENABLED"] = "false"

    import app.application.use_cases.get_dataset_detail as dataset_detail_use_case_module
    import app.application.use_cases.get_resource_detail as resource_detail_use_case_module
    import app.application.use_cases.search_datasets as search_datasets_use_case_module
    import app.infrastructure.persistence.cache_repository as cache_repository_module
    import app.infrastructure.persistence.database as database_module
    import app.infrastructure.persistence.models as models_module
    import app.infrastructure.persistence.query_cache_repository as query_cache_repository_module
    import app.infrastructure.persistence.search_repository as search_repository_module
    import app.main as main_module
    import app.presentation.api.v1.router as router_module

    database_module = importlib.reload(database_module)
    models_module = importlib.reload(models_module)
    cache_repository_module = importlib.reload(cache_repository_module)
    query_cache_repository_module = importlib.reload(query_cache_repository_module)
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


# ---------------------------------------------------------------------------
# PDS-46 : Tests du cache applicatif
# ---------------------------------------------------------------------------


def test_query_cache_tables_created_by_create_schema(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """T3: create_schema() cree bien les tables query_cache et cache_hit_stats."""
    import sqlite3

    database_path = tmp_path / "cache-tables.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, _, _ = _configure_api_modules(enable_query_cache=True)
    database_port.create_schema()

    conn = sqlite3.connect(str(database_path))
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    conn.close()
    assert "query_cache" in tables, "query_cache table should exist after create_schema()"
    assert "cache_hit_stats" in tables, "cache_hit_stats table should exist after create_schema()"


def test_internal_cache_stats_endpoint(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """T4a: GET /internal/cache/stats retourne les metriques initiales a zero."""
    database_path = tmp_path / "cache-stats-empty.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, _, app = _configure_api_modules(enable_query_cache=True)
    database_port.create_schema()

    client = cast(Any, TestClient(app))
    response = cast(Response, client.get("/api/v1/internal/cache/stats"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["hits"] == 0
    assert data["misses"] == 0
    assert data["stale_entries"] == 0
    assert data["total_entries"] == 0
    assert data["hit_ratio"] == 0.0


def test_internal_cache_stats_after_search(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """T4b: GET /internal/cache/stats reflete les hits/misses apres usage."""
    database_path = tmp_path / "cache-stats-used.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, cache_repository, app = _configure_api_modules(enable_query_cache=True)
    database_port.create_schema()
    _populate_cache_nominale(cache_repository)

    client = cast(Any, TestClient(app))

    # Premier appel: miss (cache vide)
    response1 = cast(Response, client.get("/api/v1/search?q=mobilite"))
    assert response1.status_code == 200

    stats1 = cast(Response, client.get("/api/v1/internal/cache/stats"))
    data1 = cast(dict[str, Any], stats1.json())
    assert data1["total_entries"] >= 1, "Au moins une entree de cache creee"
    assert data1["misses"] >= 1, "Premier appel = miss"

    # Deuxieme appel identique: hit
    response2 = cast(Response, client.get("/api/v1/search?q=mobilite"))
    assert response2.status_code == 200

    stats2 = cast(Response, client.get("/api/v1/internal/cache/stats"))
    data2 = cast(dict[str, Any], stats2.json())
    assert data2["hits"] >= 1, "Deuxieme appel = hit"
    assert data2["hit_ratio"] > 0.0


def test_internal_cache_reset_stats_endpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """T4c: POST /internal/cache/reset-stats reinitialise les compteurs."""
    database_path = tmp_path / "cache-reset.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, cache_repository, app = _configure_api_modules(enable_query_cache=True)
    database_port.create_schema()
    _populate_cache_nominale(cache_repository)

    client = cast(Any, TestClient(app))

    # Generer un hit
    client.get("/api/v1/search?q=mobilite")
    client.get("/api/v1/search?q=mobilite")

    # Verifier que les compteurs sont non nuls
    stats_before = cast(Response, client.get("/api/v1/internal/cache/stats"))
    data_before = cast(dict[str, Any], stats_before.json())
    assert data_before["hits"] >= 1

    # Reset sans token (dev local, pas de INTERNAL_API_TOKEN defini)
    reset_response = cast(Response, client.post("/api/v1/internal/cache/reset-stats"))
    assert reset_response.status_code == 200
    assert cast(dict[str, str], reset_response.json())["message"] == "Cache stats reset"

    # Verifier que les compteurs sont a zero
    stats_after = cast(Response, client.get("/api/v1/internal/cache/stats"))
    data_after = cast(dict[str, Any], stats_after.json())
    assert data_after["hits"] == 0
    assert data_after["misses"] == 0
    assert data_after["stale_entries"] == 0


def test_internal_cache_reset_stats_requires_token_when_configured(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """T4d: POST /internal/cache/reset-stats refuse sans token si INTERNAL_API_TOKEN defini."""
    database_path = tmp_path / "cache-reset-token.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "secret-token")

    database_port, _, app = _configure_api_modules(enable_query_cache=True)
    database_port.create_schema()

    client = cast(Any, TestClient(app))

    # Sans token → 401
    response_no_token = cast(Response, client.post("/api/v1/internal/cache/reset-stats"))
    assert response_no_token.status_code == 401

    # Mauvais token → 401
    response_bad_token = cast(
        Response,
        client.post(
            "/api/v1/internal/cache/reset-stats",
            headers={"X-Internal-Token": "wrong"},
        ),
    )
    assert response_bad_token.status_code == 401

    # Bon token → 200
    response_ok = cast(
        Response,
        client.post(
            "/api/v1/internal/cache/reset-stats",
            headers={"X-Internal-Token": "secret-token"},
        ),
    )
    assert response_ok.status_code == 200


def test_query_cache_disabled_flag_turns_off_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """T5: QUERY_CACHE_ENABLED=false desactive le cache applicatif (pas de hit)."""
    database_path = tmp_path / "cache-disabled.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    # QUERY_CACHE_ENABLED n'est pas force → false par la fixture

    database_port, cache_repository, app = _configure_api_modules(enable_query_cache=False)
    database_port.create_schema()
    _populate_cache_nominale(cache_repository)

    client = cast(Any, TestClient(app))

    # Premier appel
    response1 = cast(Response, client.get("/api/v1/search?q=mobilite"))
    assert response1.status_code == 200

    # Deuxieme appel: sans cache, pas de hit
    response2 = cast(Response, client.get("/api/v1/search?q=mobilite"))
    assert response2.status_code == 200

    # Les stats de cache devraient etre vides (pas d'ecriture cache)
    stats = cast(Response, client.get("/api/v1/internal/cache/stats"))
    data = cast(dict[str, Any], stats.json())
    assert data["total_entries"] == 0, "Aucune entree de cache si flag OFF"
    assert data["hits"] == 0, "Pas de hit si flag OFF"
    assert data["misses"] == 0, "Pas de miss non plus si flag OFF (cache non utilise)"


def test_cache_ttl_expired_bypasses_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """T1a: Une entree de cache avec TTL expire est ignoree (stale + bypass)."""

    database_path = tmp_path / "cache-ttl.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, cache_repository, app = _configure_api_modules(enable_query_cache=True)
    database_port.create_schema()
    _populate_cache_nominale(cache_repository)

    client = cast(Any, TestClient(app))

    # Injecter une entree de cache avec un created_at vieux (TTL 1 seconde)
    from app.domain.cache_invalidation import CacheEndpointType, build_search_cache_key

    stale_key = build_search_cache_key(
        query="vieux",
        offset=0,
        limit=20,
        org_filter=None,
        format_filter=None,
        tag_filter=None,
        sort="modified_desc",
    )
    from app.infrastructure.persistence.database import SessionLocal
    from app.infrastructure.persistence.models import QueryCacheModel

    with SessionLocal() as session:
        session.merge(
            QueryCacheModel(
                key=stale_key,
                endpoint_type=CacheEndpointType.SEARCH.value,
                response_json='{"total":0,"offset":0,"limit":20,"datasets":[]}',
                created_at="2020-01-01T00:00:00+00:00",  # Tres vieux
                hit_count=0,
            )
        )
        session.commit()

    # Recherche qui matcherait la cle stale si le TTL etait ignore
    response = cast(Response, client.get("/api/v1/search?q=vieux"))
    assert response.status_code == 200

    # Verifier que l'entree stale a ete comptee comme stale
    stats = cast(Response, client.get("/api/v1/internal/cache/stats"))
    data = cast(dict[str, Any], stats.json())
    assert data["stale_entries"] >= 1, "L'entree perimee doit etre comptee comme stale"


def test_cache_json_malformed_bypasses(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """T1b: Un JSON malforme dans le cache ne casse pas l'API (bypass + warning)."""
    database_path = tmp_path / "cache-json.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, cache_repository, app = _configure_api_modules(enable_query_cache=True)
    database_port.create_schema()
    _populate_cache_nominale(cache_repository)

    client = cast(Any, TestClient(app))

    # Injecter du JSON invalide dans le cache
    from app.domain.cache_invalidation import CacheEndpointType, build_search_cache_key

    bad_key = build_search_cache_key(
        query="corrompu",
        offset=0,
        limit=20,
        org_filter=None,
        format_filter=None,
        tag_filter=None,
        sort="modified_desc",
    )
    from app.infrastructure.persistence.database import SessionLocal
    from app.infrastructure.persistence.models import QueryCacheModel

    with SessionLocal() as session:
        session.merge(
            QueryCacheModel(
                key=bad_key,
                endpoint_type=CacheEndpointType.SEARCH.value,
                response_json="NOT VALID JSON {{{[][",
                created_at="2026-06-26T10:00:00+00:00",
                hit_count=0,
            )
        )
        session.commit()

    # La recherche ne doit pas echouer malgre le JSON invalide
    response = cast(Response, client.get("/api/v1/search?q=corrompu"))
    assert response.status_code == 200
