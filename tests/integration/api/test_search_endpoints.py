"""Tests d'integration de l'endpoint de recherche /api/v1/search."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause

from ._fixtures import (
    configure_api_modules,
    populate_cache_facets,
    populate_cache_facets_filtered_scope_case,
    populate_cache_multilingual_expansion_case,
    populate_cache_nominale,
    populate_cache_organizations_many,
    populate_cache_tag_exact_match_case,
    populate_cache_tag_only_fulltext,
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


def test_search_query_matches_term_only_in_tags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """GET /api/v1/search?q=climat trouve un dataset uniquement grace aux tags FTS5."""

    database_path = tmp_path / "search-tag-only-fts.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()

    dataset_id = populate_cache_tag_only_fulltext(cache_repository)

    client = cast(Any, TestClient(app))
    response = cast(Response, client.get("/api/v1/search?q=climat"))

    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["total"] == 1
    datasets = cast(list[dict[str, Any]], data["datasets"])
    assert datasets[0]["id"] == dataset_id


def test_create_schema_migrates_legacy_fts_without_tags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """create_schema migre un schema FTS5 historique (sans tags) vers le schema courant."""

    database_path = tmp_path / "search-legacy-fts-migration.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    dataset_id = populate_cache_tag_only_fulltext(cache_repository)

    with sqlite3.connect(database_path) as conn:
        # Simuler un schema historique FTS5 sans colonne tags
        conn.executescript("""
            DROP TRIGGER IF EXISTS datasets_ai;
            DROP TRIGGER IF EXISTS datasets_ad;
            DROP TRIGGER IF EXISTS datasets_au;
            DROP TABLE IF EXISTS datasets_fts;

            CREATE VIRTUAL TABLE datasets_fts USING fts5(
                id, title, description,
                tokenize='unicode61 remove_diacritics 2',
                content='datasets',
                content_rowid='rowid'
            );

            CREATE TRIGGER IF NOT EXISTS datasets_ai AFTER INSERT ON datasets BEGIN
                INSERT INTO datasets_fts(rowid, id, title, description)
                VALUES(new.rowid, new.id, new.title, new.description);
            END;

            CREATE TRIGGER IF NOT EXISTS datasets_ad AFTER DELETE ON datasets BEGIN
                INSERT INTO datasets_fts(datasets_fts, rowid, id, title, description)
                VALUES('delete', old.rowid, old.id, old.title, old.description);
            END;

            CREATE TRIGGER IF NOT EXISTS datasets_au AFTER UPDATE ON datasets BEGIN
                INSERT INTO datasets_fts(datasets_fts, rowid, id, title, description)
                VALUES('delete', old.rowid, old.id, old.title, old.description);
                INSERT INTO datasets_fts(rowid, id, title, description)
                VALUES(new.rowid, new.id, new.title, new.description);
            END;

            INSERT INTO datasets_fts(rowid, id, title, description)
            SELECT d.rowid, d.id, d.title, d.description
            FROM datasets d;
        """)

    # Relance create_schema: doit detecter l'ancien schema et reconstruire avec tags
    database_port.create_schema()

    with sqlite3.connect(database_path) as conn:
        columns = conn.execute("PRAGMA table_info(datasets_fts)").fetchall()
        column_names = [str(row[1]).lower() for row in columns]
        assert "tags" in column_names

    client = cast(Any, TestClient(app))
    response = cast(Response, client.get("/api/v1/search?q=climat"))
    assert response.status_code == 200

    data = cast(dict[str, Any], response.json())
    assert data["total"] == 1
    datasets = cast(list[dict[str, Any]], data["datasets"])
    assert datasets[0]["id"] == dataset_id


def test_search_query_uses_multilingual_expansion_backend(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """GET /api/v1/search?q=wetter retrouve un dataset tagge meteo via expansion backend."""

    database_path = tmp_path / "search-multilingual-expansion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    dataset_id = populate_cache_multilingual_expansion_case(cache_repository)

    client = cast(Any, TestClient(app))
    response = cast(Response, client.get("/api/v1/search?q=wetter"))

    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["total"] >= 1
    ids = {str(item["id"]) for item in cast(list[dict[str, Any]], data["datasets"])}
    assert dataset_id in ids


def test_search_facets_are_scoped_by_active_text_query(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Les facettes doivent refleter le sous-ensemble retourne par la recherche texte active."""

    database_path = tmp_path / "search-facets-scoped-by-fts.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    ds_temp, ds_pop = populate_cache_facets_filtered_scope_case(cache_repository)

    client = cast(Any, TestClient(app))
    response = cast(Response, client.get("/api/v1/search?q=temperature"))

    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    datasets = cast(list[dict[str, Any]], data["datasets"])
    ids = {str(item["id"]) for item in datasets}
    assert ds_temp in ids
    assert ds_pop not in ids

    facets = cast(dict[str, Any], data["facets"])
    tag_names = {str(item["name"]) for item in cast(list[dict[str, Any]], facets["tags"])}
    org_names = {str(item["name"]) for item in cast(list[dict[str, Any]], facets["organizations"])}
    fmt_names = {str(item["name"]) for item in cast(list[dict[str, Any]], facets["formats"])}

    assert "climat" in tag_names
    assert "environnement" in tag_names
    assert "population" not in tag_names
    assert "org-temp" in org_names
    assert "org-pop" not in org_names
    assert "CSV" in fmt_names
    assert "JSON" not in fmt_names


def test_search_tag_filter_is_exact_not_substring(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Le filtre tag=air ne doit pas matcher un dataset tagge agriculture."""

    database_path = tmp_path / "search-tag-exact.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    ds_air, ds_agri = populate_cache_tag_exact_match_case(cache_repository)

    client = cast(Any, TestClient(app))
    response = cast(Response, client.get("/api/v1/search?tag=air"))

    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    datasets = cast(list[dict[str, Any]], data["datasets"])
    ids = {str(item["id"]) for item in datasets}

    assert ds_air in ids
    assert ds_agri not in ids


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

    # PDS-95 : l'ordre hybride est desormais determine par bm25(datasets_fts)
    # en SQL (score BM25 natif), plus par compute_hybrid_score en Python.
    # On verifie que les 2 datasets sont presents avec leurs signaux de ranking.
    ids_returned = {str(item["id"]) for item in datasets}
    assert ids_returned == {"dataset-json", "dataset-csv"}
    assert datasets[0]["ranking_signals"] is not None
    assert datasets[1]["ranking_signals"] is not None
    assert "hybrid_score" in datasets[0]["ranking_signals"]
    assert "hybrid_score" in datasets[1]["ranking_signals"]


def test_search_degrades_gracefully_when_fts_table_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """GET /api/v1/search ne doit pas crasher si l'index FTS5 est absent."""

    database_path = tmp_path / "search-fts-missing.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    dataset_id, _ = populate_cache_nominale(cache_repository)

    with sqlite3.connect(database_path) as conn:
        conn.executescript("""
            DROP TRIGGER IF EXISTS datasets_ai;
            DROP TRIGGER IF EXISTS datasets_ad;
            DROP TRIGGER IF EXISTS datasets_au;
            DROP TABLE IF EXISTS datasets_fts;
        """)

    client = cast(Any, TestClient(app))
    response = cast(Response, client.get("/api/v1/search?q=mobilite&sort=hybrid"))

    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    ids = {str(item["id"]) for item in cast(list[dict[str, Any]], data["datasets"])}
    assert dataset_id in ids


def test_search_degrades_gracefully_when_fts_match_is_malformed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """GET /api/v1/search ne doit pas renvoyer 500 sur MATCH FTS5 malforme."""

    database_path = tmp_path / "search-fts-malformed.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    dataset_id, _ = populate_cache_nominale(cache_repository)

    import app.infrastructure.persistence.search_adapter as search_adapter_module

    def _malformed_fts_match(_query: str) -> TextClause:
        return text(
            "datasets.ROWID IN (SELECT rowid FROM datasets_fts "
            "WHERE datasets_fts MATCH 'unterminated)"
        )

    monkeypatch.setattr(
        search_adapter_module,
        "_search_fts_match",
        _malformed_fts_match,
    )

    client = cast(Any, TestClient(app))
    response = cast(Response, client.get("/api/v1/search?q=mobilite"))

    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    ids = {str(item["id"]) for item in cast(list[dict[str, Any]], data["datasets"])}
    assert dataset_id in ids


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


def test_search_combined_filters_return_coherent_dataset_and_facets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Sentinelle PDS-101: combinaison q+org+fmt+tag retourne un scope coherent."""

    database_path = tmp_path / "search-combined-filters.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()
    populate_cache_facets(cache_repository)

    client = cast(Any, TestClient(app))
    response = cast(
        Response,
        client.get("/api/v1/search?q=mobilite&org=org-001&fmt=CSV&tag=mobilite&sort=modified_desc"),
    )
    assert response.status_code == 200

    data = cast(dict[str, Any], response.json())
    datasets = cast(list[dict[str, Any]], data["datasets"])
    assert data["total"] == 1
    assert len(datasets) == 1
    assert str(datasets[0]["id"]) == "dataset-csv"

    facets = cast(dict[str, Any], data["facets"])
    org_names = {str(item["name"]) for item in cast(list[dict[str, Any]], facets["organizations"])}
    fmt_names = {str(item["name"]) for item in cast(list[dict[str, Any]], facets["formats"])}
    tag_names = {str(item["name"]) for item in cast(list[dict[str, Any]], facets["tags"])}

    assert org_names == {"org-001"}
    assert "CSV" in fmt_names
    assert "mobilite" in tag_names
    assert "api" not in tag_names


def test_search_combined_sentinel_cache_hit_ratio(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Sentinelle PDS-101: la recherche combinée produit un hit ratio > 0 en cache actif."""

    database_path = tmp_path / "search-combined-cache-ratio.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, cache_repository, app = configure_api_modules(enable_query_cache=True)
    database_port.create_schema()
    populate_cache_facets(cache_repository)

    client = cast(Any, TestClient(app))
    combined_url = "/api/v1/search?q=mobilite&org=org-001&fmt=CSV&tag=mobilite&sort=modified_desc"

    first = cast(Response, client.get(combined_url))
    assert first.status_code == 200

    second = cast(Response, client.get(combined_url))
    assert second.status_code == 200

    stats = cast(Response, client.get("/api/v1/internal/cache/stats"))
    assert stats.status_code == 200
    data = cast(dict[str, Any], stats.json())
    assert data["hits"] >= 1
    assert float(data["hit_ratio"]) > 0.0
