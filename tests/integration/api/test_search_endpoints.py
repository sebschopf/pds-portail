"""Tests d'integration de l'endpoint de recherche /api/v1/search."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from ._fixtures import (
    configure_api_modules,
    populate_cache_facets,
    populate_cache_nominale,
    populate_cache_organizations_many,
)


def test_search_empty_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/search sur un cache vide retourne resultats vides."""

    database_path = tmp_path / "search-empty.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, _, app = configure_api_modules()
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

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()

    dataset_id, _ = populate_cache_nominale(cache_repository)

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

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()

    dataset_id, _ = populate_cache_nominale(cache_repository)

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

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()

    populate_cache_nominale(cache_repository)

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

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    populate_cache_facets(cache_repository)

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

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    populate_cache_facets(cache_repository)

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

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    populate_cache_facets(cache_repository)

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

    database_port, _, app = configure_api_modules()
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

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    populate_cache_organizations_many(cache_repository)

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
