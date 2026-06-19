"""Tests d'integration de l'exposition OpenAPI selon l'environnement."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _configure_main_module():
    """Recharge l'application en tenant compte des variables d'environnement."""

    import app.core.config as config_module
    import app.infrastructure.persistence.database as database_module
    import app.main as main_module

    config_module.get_settings.cache_clear()
    database_module = importlib.reload(database_module)
    main_module = importlib.reload(main_module)

    return database_module, main_module


def test_docs_hidden_when_expose_api_docs_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Les pages de doc ne sont pas accessibles quand EXPOSE_API_DOCS=false."""

    database_path = tmp_path / "docs-hidden.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("EXPOSE_API_DOCS", "false")

    database_module, main_module = _configure_main_module()
    database_module.create_schema()

    client = TestClient(main_module.app)

    docs_response = client.get("/docs")
    redoc_response = client.get("/redoc")
    openapi_response = client.get("/api/v1/openapi.json")

    assert docs_response.status_code == 404
    assert redoc_response.status_code == 404
    assert openapi_response.status_code == 404


def test_docs_exposed_when_expose_api_docs_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Les pages de doc sont disponibles pour les environnements internes/dev."""

    database_path = tmp_path / "docs-enabled.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("EXPOSE_API_DOCS", "true")

    database_module, main_module = _configure_main_module()
    database_module.create_schema()

    client = TestClient(main_module.app)

    docs_response = client.get("/docs")
    redoc_response = client.get("/redoc")
    openapi_response = client.get("/api/v1/openapi.json")

    assert docs_response.status_code == 200
    assert redoc_response.status_code == 200
    assert openapi_response.status_code == 200

    payload = openapi_response.json()
    assert payload["info"]["title"] == "PDS-Portail Backend"
    assert payload["openapi"]
