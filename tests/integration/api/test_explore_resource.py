"""Tests d'intégration endpoint POST /api/v1/resources/{id}/explore (PDS-81).

Valide la protection par clé API, la validation du format, et les réponses.

Conformité DoD Tests (PDS-108 + R004 fiabilisation):
- Temps déterministe (pas de datetime.now() implicite)
- Assertions sur effets métier (used_this_month s'incrémente)
- Indépendance à l'ordre d'exécution (fixtures isolées par test)
- Cleanup automatique via fixtures (zéro code teardown)

SOLID/SRP: Chaque fixture a UNE responsabilité, tests ultra-lisibles.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.domain.ckan_normalized import Dataset, NormalizedBatch, Organization, Resource
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import LicenseModel

from ._fixtures import configure_api_modules

# Constantes déterministes (R004 #2: pas de datetime.now() implicite)
TEST_TIMESTAMP = "2026-07-02T12:00:00+00:00"
TEST_API_KEY = "test-api-key-12345678901234567890"
TEST_API_KEY_HASH = hashlib.sha256(TEST_API_KEY.encode()).hexdigest()


@pytest.fixture
def app_with_temp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    """App FastAPI configurée avec BD SQLite isolée par test (R004 #3: indépendance).

    Crée une BD temporaire fraîche par test, configure monkeypatch,
    initialise le schéma. Cleanup automatique via tmp_path.
    """
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    database_port, _, app = configure_api_modules()
    database_port.create_schema()

    return app


@pytest.fixture
def valid_license(app_with_temp_db: Any) -> LicenseModel:  # noqa: ARG001
    """Crée une licence valide réutilisable (SOLID: single responsibility).

    Factory pour créer une licence de test avec tous les champs requis.
    Retourne LicenseModel (modèle ORM) pour pouvoir vérifier l'effet de bord
    (used_this_month s'incrémente) dans les tests.
    app_with_temp_db : dépendance pour l'isolation de BD (utilisée implicitement).
    Cleanup via fixture scope (SessionLocal().close() implicite).
    """
    session = SessionLocal()
    try:
        license_model = LicenseModel(
            id="test-license",
            key_hash=TEST_API_KEY_HASH,
            plan="pro",
            quota_monthly=1000,
            used_this_month=0,
            created_at="2026-07-01T00:00:00Z",
            expires_at="2026-08-01T00:00:00Z",
        )
        session.add(license_model)
        session.commit()
        return license_model
    finally:
        session.close()


@pytest.fixture
def test_csv_resource(app_with_temp_db: Any, tmp_path: Path) -> str:  # noqa: ARG001
    """Crée une ressource CSV de test et retourne son ID (SOLID: single purpose).

    Utilise un fichier local pour éviter toute dépendance réseau pendant le parsing.
    app_with_temp_db : dépendance pour l'isolation de BD (utilisée implicitement).
    """
    csv_path = tmp_path / "sample-resource.csv"
    csv_path.write_text(
        "commune,population\nGenève,203856\nLausanne,140202\nBerne,134794\nZürich,421878\nWinterthur,115129\n",
        encoding="utf-8",
    )

    _, cache_repository, _ = configure_api_modules()

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
        url=csv_path.as_uri(),
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

    cache_repository.upsert_normalized_batch(
        NormalizedBatch(organizations=[org], datasets=[dataset], resources=[resource])
    )

    resource_id = resource.id
    return resource_id


@pytest.fixture
def test_json_resource(app_with_temp_db: Any, tmp_path: Path) -> str:  # noqa: ARG001
    """Crée une ressource JSON de test locale et retourne son ID."""

    json_path = tmp_path / "sample-resource.json"
    json_path.write_text(
        json.dumps(
            [
                {"commune": "Genève", "population": 203856},
                {"commune": "Lausanne", "population": 140202},
                {"commune": "Berne", "population": 134794},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    _, cache_repository, _ = configure_api_modules()

    org = Organization(
        id="org-json",
        name="Observatoire urbain",
        description="Donnees publiques",
        ckan_url="https://opendata.swiss/organization/observatoire-urbain",
        last_synced="2026-06-13T10:00:00Z",
    )
    dataset = Dataset(
        id="dataset-json",
        org_id="org-json",
        title="Population par commune",
        description="Jeu de donnees JSON",
        tags=["population", "commune"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=79,
        completeness=91,
        freshness_days=2,
        ckan_url="https://opendata.swiss/dataset/population",
    )
    resource = Resource(
        id="resource-json",
        dataset_id="dataset-json",
        name="Export JSON",
        format="JSON",
        url=json_path.as_uri(),
        size_bytes=3456,
        created="2026-01-01T08:00:00Z",
        last_modified="2026-06-10T15:30:00Z",
    )

    cache_repository.upsert_normalized_batch(
        NormalizedBatch(organizations=[org], datasets=[dataset], resources=[resource])
    )

    return resource.id


# ────────────────────────────────────────────────────────────────────────────
# TESTS (R004 #1: nominal + erreurs + limites)
# Chaque test = une assertion métier forte, zéro duplication de setup
# ────────────────────────────────────────────────────────────────────────────


def test_explore_resource_without_api_key(app_with_temp_db: Any) -> None:
    """POST /resources/{id}/explore sans X-API-Key → 401 (erreur)."""
    client = cast(Any, TestClient(app_with_temp_db))

    response = cast(Response, client.post("/api/v1/resources/any/explore"))

    assert response.status_code == 401
    assert "Missing X-API-Key" in response.json()["detail"]


def test_explore_resource_with_invalid_key(app_with_temp_db: Any) -> None:
    """POST /resources/{id}/explore avec clé invalide → 401 (erreur)."""
    client = cast(Any, TestClient(app_with_temp_db))

    response = cast(
        Response,
        client.post(
            "/api/v1/resources/any/explore",
            headers={"X-API-Key": "invalid-key-999"},
        ),
    )

    assert response.status_code == 401
    assert "Invalid or expired" in response.json()["detail"]


def test_explore_resource_not_found(
    app_with_temp_db: Any, valid_license: LicenseModel
) -> None:  # noqa: ARG001
    """POST /resources/{id}/explore ressource inexistante → 404 (limite)."""
    assert valid_license is not None
    client = cast(Any, TestClient(app_with_temp_db))

    response = cast(
        Response,
        client.post(
            "/api/v1/resources/nonexistent/explore",
            headers={"X-API-Key": TEST_API_KEY},
        ),
    )

    assert response.status_code == 404


def test_explore_resource_unsupported_format(
    app_with_temp_db: Any, valid_license: LicenseModel
) -> None:  # noqa: ARG001
    """POST /resources/{id}/explore format XML (non supporté) → 422 (limite)."""
    assert valid_license is not None
    _, cache_repository, _ = configure_api_modules()

    # Crée ressource XML pour test du rejet de format
    org = Organization(
        id="org-1", name="Test", description="Test", last_synced="2026-07-02T00:00:00Z"
    )
    dataset = Dataset(id="ds-1", org_id="org-1", title="Test", created="2026-07-02T00:00:00Z")
    resource = Resource(
        id="res-xml",
        dataset_id="ds-1",
        name="Data",
        format="XML",
        url="http://x.com/data.xml",
    )
    cache_repository.upsert_normalized_batch(NormalizedBatch([org], [dataset], [resource]))

    client = cast(Any, TestClient(app_with_temp_db))
    response = cast(
        Response,
        client.post(
            "/api/v1/resources/res-xml/explore",
            headers={"X-API-Key": TEST_API_KEY},
        ),
    )

    assert response.status_code == 422


def test_explore_resource_success_csv(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    test_csv_resource: str,
) -> None:  # noqa: ARG001
    """POST /resources/{id}/explore CSV valide → 200 + structure (nominal, R004 #2)."""

    assert valid_license is not None
    client = cast(Any, TestClient(app_with_temp_db))
    response = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": TEST_API_KEY},
        ),
    )

    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["resource_id"] == test_csv_resource
    assert data["format"] == "csv"
    assert isinstance(data["parsed_at"], str)
    assert data["row_count"] == 5
    assert data["cached"] is False
    assert [column["name"] for column in data["columns"]] == ["commune", "population"]
    assert data["columns"][0]["detected_type"] == "string"
    assert data["columns"][1]["detected_type"] == "integer"
    assert data["columns"][1]["stats"]["min"] == 115129.0
    assert data["columns"][1]["stats"]["max"] == 421878.0


def test_explore_resource_success_json(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    test_json_resource: str,
) -> None:  # noqa: ARG001
    """POST /resources/{id}/explore JSON valide → 200 + structure parsée."""

    assert valid_license is not None
    client = cast(Any, TestClient(app_with_temp_db))
    response = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_json_resource}/explore",
            headers={"X-API-Key": TEST_API_KEY},
        ),
    )

    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["resource_id"] == test_json_resource
    assert data["format"] == "json"
    assert data["row_count"] == 3
    assert data["cached"] is False
    assert [column["name"] for column in data["columns"]] == ["commune", "population"]
    assert data["columns"][1]["stats"]["median"] == 140202.0


def test_explore_resource_cached_second_call(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    test_csv_resource: str,
) -> None:  # noqa: ARG001
    """Deux appels successifs retournent un cache hit au second passage."""

    assert valid_license is not None
    client = cast(Any, TestClient(app_with_temp_db))

    first_response = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": TEST_API_KEY},
        ),
    )
    second_response = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": TEST_API_KEY},
        ),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_data = cast(dict[str, Any], first_response.json())
    second_data = cast(dict[str, Any], second_response.json())
    assert first_data["cached"] is False
    assert second_data["cached"] is True
    assert second_data["columns"] == first_data["columns"]


def test_explore_resource_malformed_json_returns_422(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    tmp_path: Path,
) -> None:  # noqa: ARG001
    """Un JSON invalide retourne 422 avec une erreur de parsing propre."""

    assert valid_license is not None
    json_path = tmp_path / "broken.json"
    json_path.write_text('[{"commune": "Genève", "population": 1}', encoding="utf-8")

    _, cache_repository, _ = configure_api_modules()
    org = Organization(
        id="org-broken",
        name="Observatoire",
        description="Donnees",
        ckan_url="https://opendata.swiss/organization/observatoire",
        last_synced="2026-06-13T10:00:00Z",
    )
    dataset = Dataset(
        id="dataset-broken",
        org_id="org-broken",
        title="JSON cassé",
        description="Jeu de donnees invalide",
        tags=["json"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=50,
        completeness=50,
        freshness_days=10,
        ckan_url="https://opendata.swiss/dataset/json-broken",
    )
    resource = Resource(
        id="resource-broken",
        dataset_id="dataset-broken",
        name="Broken JSON",
        format="JSON",
        url=json_path.as_uri(),
    )
    cache_repository.upsert_normalized_batch(
        NormalizedBatch(organizations=[org], datasets=[dataset], resources=[resource])
    )

    client = cast(Any, TestClient(app_with_temp_db))
    response = cast(
        Response,
        client.post(
            f"/api/v1/resources/{resource.id}/explore",
            headers={"X-API-Key": TEST_API_KEY},
        ),
    )

    assert response.status_code == 422
    assert "Failed to parse resource" in response.json()["detail"]


def test_explore_resource_increments_usage(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    test_csv_resource: str,
) -> None:  # noqa: ARG001
    """POST /resources/{id}/explore incrémente used_this_month (effet métier, R004 #4).

    Assertion comportementale forte: vérifie l'effet de bord (0→1→2),
    pas juste le statut HTTP 200.
    valid_license : fixture pour créer la licence en BD (non utilisée directement).
    """
    assert valid_license is not None
    client = cast(Any, TestClient(app_with_temp_db))

    # AVANT: used = 0
    session = SessionLocal()
    try:
        lic = session.query(LicenseModel).filter_by(id="test-license").first()
        assert lic is not None
        assert lic.used_this_month == 0
    finally:
        session.close()

    # Premier appel
    response1 = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": TEST_API_KEY},
        ),
    )
    assert response1.status_code == 200

    # APRÈS appel 1: used = 1
    session = SessionLocal()
    try:
        lic = session.query(LicenseModel).filter_by(id="test-license").first()
        assert lic is not None
        assert lic.used_this_month == 1
    finally:
        session.close()

    # Deuxième appel
    response2 = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": TEST_API_KEY},
        ),
    )
    assert response2.status_code == 200

    # APRÈS appel 2: used = 2
    session = SessionLocal()
    try:
        lic = session.query(LicenseModel).filter_by(id="test-license").first()
        assert lic is not None
        assert lic.used_this_month == 2
    finally:
        session.close()
