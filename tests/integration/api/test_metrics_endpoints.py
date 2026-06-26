"""Tests d'integration des endpoints metriques d'usage (PDS-58).

Verifie top-queries et zero-results exposes depuis le cache query_cache.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from ._fixtures import configure_api_modules, populate_cache_nominale


def _inject_query_cache_entries() -> None:
    """Injecte directement des entrees query_cache pour les tests metriques."""
    import json

    from app.infrastructure.persistence.database import SessionLocal
    from app.infrastructure.persistence.models import QueryCacheModel

    with SessionLocal() as session:
        # 3 entrees normales avec hit_count varie
        entries = [
            QueryCacheModel(
                key="search:q=mobilite:offset=0:limit=20",
                endpoint_type="search",
                response_json=json.dumps({"total": 5, "offset": 0, "limit": 20, "datasets": []}),
                created_at="2026-06-20T10:00:00+00:00",
                hit_count=42,
            ),
            QueryCacheModel(
                key="search:q=transport:offset=0:limit=20",
                endpoint_type="search",
                response_json=json.dumps({"total": 3, "offset": 0, "limit": 20, "datasets": []}),
                created_at="2026-06-21T10:00:00+00:00",
                hit_count=15,
            ),
            QueryCacheModel(
                key="search:q=meteo:offset=0:limit=20",
                endpoint_type="search",
                response_json=json.dumps({"total": 1, "offset": 0, "limit": 20, "datasets": []}),
                created_at="2026-06-22T10:00:00+00:00",
                hit_count=7,
            ),
            # 2 entrees avec total=0 (zero results)
            QueryCacheModel(
                key="search:q=inexistant:offset=0:limit=20",
                endpoint_type="search",
                response_json=json.dumps({"total": 0, "offset": 0, "limit": 20, "datasets": []}),
                created_at="2026-06-19T10:00:00+00:00",
                hit_count=3,
            ),
            QueryCacheModel(
                key="search:q=introuvable:offset=0:limit=20",
                endpoint_type="search",
                response_json=json.dumps({"total": 0, "offset": 0, "limit": 20, "datasets": []}),
                created_at="2026-06-18T10:00:00+00:00",
                hit_count=1,
            ),
        ]
        for entry in entries:
            session.merge(entry)
        session.commit()


def test_top_queries_returns_ranked_by_hit_count(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """T1: GET /internal/metrics/top-queries retourne les N requetes triees par hit_count desc."""
    database_path = tmp_path / "metrics-top.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, _, app = configure_api_modules(enable_query_cache=True)
    database_port.create_schema()
    _inject_query_cache_entries()

    client = cast(Any, TestClient(app))

    # Default limit=20
    response = cast(Response, client.get("/api/v1/internal/metrics/top-queries"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    queries = cast(list[dict[str, Any]], data["queries"])
    assert len(queries) == 5  # Toutes les entrees
    # Verifier l'ordre decroissant de hit_count
    hit_counts = [q["hit_count"] for q in queries]
    assert hit_counts == sorted(hit_counts, reverse=True), "Doit etre trie decroissant"
    assert queries[0]["hit_count"] == 42
    assert queries[0]["query_key"] == "search:q=mobilite:offset=0:limit=20"


def test_top_queries_respects_limit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """T2: GET /internal/metrics/top-queries?limit=2 retourne seulement 2 entrees."""
    database_path = tmp_path / "metrics-top-limit.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, _, app = configure_api_modules(enable_query_cache=True)
    database_port.create_schema()
    _inject_query_cache_entries()

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/internal/metrics/top-queries?limit=2"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    queries = cast(list[dict[str, Any]], data["queries"])
    assert len(queries) == 2
    assert queries[0]["hit_count"] == 42
    assert queries[1]["hit_count"] == 15


def test_top_queries_limit_bounds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """T3: limit < 1 et > 100 sont rejetes (validation Query)."""
    database_path = tmp_path / "metrics-top-bounds.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, _, app = configure_api_modules(enable_query_cache=True)
    database_port.create_schema()

    client = cast(Any, TestClient(app))

    # limit=0 → 422
    response = cast(Response, client.get("/api/v1/internal/metrics/top-queries?limit=0"))
    assert response.status_code == 422

    # limit=101 → 422
    response = cast(Response, client.get("/api/v1/internal/metrics/top-queries?limit=101"))
    assert response.status_code == 422


def test_zero_results_returns_only_total_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """T4: GET /internal/metrics/zero-results retourne uniquement les entrees avec total=0."""
    database_path = tmp_path / "metrics-zero.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, _, app = configure_api_modules(enable_query_cache=True)
    database_port.create_schema()
    _inject_query_cache_entries()

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/internal/metrics/zero-results"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    queries = cast(list[dict[str, Any]], data["queries"])
    assert len(queries) == 2, "Seulement les 2 entrees avec total=0"
    assert data["count"] == 2
    # Verifier que ce sont bien les zero-results
    keys = {q["query_key"] for q in queries}
    assert keys == {
        "search:q=inexistant:offset=0:limit=20",
        "search:q=introuvable:offset=0:limit=20",
    }
    for q in queries:
        assert q["response_total"] == 0
        assert "endpoint_type" in q
        assert "created_at" in q


def test_zero_results_empty_when_no_zero_total(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """T5: zero-results retourne une liste vide si aucune entree avec total=0."""
    database_path = tmp_path / "metrics-zero-empty.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, cache_repository, app = configure_api_modules(enable_query_cache=True)
    database_port.create_schema()
    populate_cache_nominale(cache_repository)

    # Generer un hit pour creer une entree cache avec total>0
    client = cast(Any, TestClient(app))
    client.get("/api/v1/search?q=mobilite")

    response = cast(Response, client.get("/api/v1/internal/metrics/zero-results"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["queries"] == []
    assert data["count"] == 0


def test_metrics_endpoints_protected_by_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """T6: Les endpoints /internal/metrics/* requierent INTERNAL_API_TOKEN si configure."""
    database_path = tmp_path / "metrics-token.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "secret-token")

    database_port, _, app = configure_api_modules(enable_query_cache=True)
    database_port.create_schema()

    client = cast(Any, TestClient(app))

    # top-queries sans token → 401
    response = cast(Response, client.get("/api/v1/internal/metrics/top-queries"))
    assert response.status_code == 401

    # zero-results sans token → 401
    response = cast(Response, client.get("/api/v1/internal/metrics/zero-results"))
    assert response.status_code == 401

    # Mauvais token → 401
    response = cast(
        Response,
        client.get(
            "/api/v1/internal/metrics/top-queries",
            headers={"X-Internal-Token": "wrong"},
        ),
    )
    assert response.status_code == 401

    # Bon token → 200
    response = cast(
        Response,
        client.get(
            "/api/v1/internal/metrics/top-queries",
            headers={"X-Internal-Token": "secret-token"},
        ),
    )
    assert response.status_code == 200

    response = cast(
        Response,
        client.get(
            "/api/v1/internal/metrics/zero-results",
            headers={"X-Internal-Token": "secret-token"},
        ),
    )
    assert response.status_code == 200


def test_metrics_endpoints_open_without_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """T7: Les endpoints /internal/metrics/* sont ouverts sans INTERNAL_API_TOKEN defini."""
    database_path = tmp_path / "metrics-open.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")
    # Pas de INTERNAL_API_TOKEN defini

    database_port, _, app = configure_api_modules(enable_query_cache=True)
    database_port.create_schema()

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/internal/metrics/top-queries"))
    assert response.status_code == 200

    response = cast(Response, client.get("/api/v1/internal/metrics/zero-results"))
    assert response.status_code == 200


def test_top_queries_empty_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """T8: top-queries sur une base vide retourne une liste vide."""
    database_path = tmp_path / "metrics-empty.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("QUERY_CACHE_ENABLED", "true")

    database_port, _, app = configure_api_modules(enable_query_cache=True)
    database_port.create_schema()

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/internal/metrics/top-queries"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["queries"] == []
