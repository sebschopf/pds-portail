"""Tests d'integration des endpoints de detail dataset et resource."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from ._fixtures import configure_api_modules, populate_cache_nominale


def test_dataset_detail_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/dataset/{id} retourne 404 si dataset inexistant."""

    database_path = tmp_path / "detail-404.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, _, app = configure_api_modules()
    database_port.create_schema()

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/dataset/nonexistent"))
    assert response.status_code == 404


def test_dataset_detail_nominale(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/dataset/{id} retourne le detail complet avec ressources."""

    database_path = tmp_path / "detail-nominale.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()

    dataset_id, resource_id = populate_cache_nominale(cache_repository)

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

    database_port, _, app = configure_api_modules()
    database_port.create_schema()

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get("/api/v1/resource/nonexistent"))
    assert response.status_code == 404


def test_resource_detail_nominale(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GET /api/v1/resource/{id} retourne le detail avec reference au dataset."""

    database_path = tmp_path / "resource-nominale.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    database_port, cache_repository, app = configure_api_modules()
    database_port.create_schema()

    dataset_id, resource_id = populate_cache_nominale(cache_repository)

    client = cast(Any, TestClient(app))

    response = cast(Response, client.get(f"/api/v1/resource/{resource_id}"))
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["id"] == resource_id
    assert data["name"] == "Flux de mobilite CSV"
    assert data["format"] == "CSV"
    assert data["dataset_id"] == dataset_id
    assert data["dataset_title"] == "Donnees de mobilite urbaine"
