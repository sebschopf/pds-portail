"""Fixtures partagées pour les tests d'intégration API de l'exploration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from app.domain.ckan_normalized import Dataset, NormalizedBatch, Organization, Resource
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import LicenseModel

from ._fixtures import configure_api_modules

TEST_API_KEY = "test-api-key-12345678901234567890"
TEST_API_KEY_HASH = hashlib.sha256(TEST_API_KEY.encode()).hexdigest()


@pytest.fixture
def api_key() -> str:
    """Retourne une clé API de test stable."""

    return TEST_API_KEY


@pytest.fixture
def app_with_temp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    """App FastAPI configurée avec BD SQLite isolée par test."""

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    database_port, _, app = configure_api_modules()
    database_port.create_schema()

    return app


@pytest.fixture
def valid_license(app_with_temp_db: Any) -> LicenseModel:  # noqa: ARG001
    """Crée une licence valide en base pour les tests /explore."""

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
    """Crée une ressource CSV locale et retourne son ID."""

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

    return resource.id


@pytest.fixture
def test_json_resource(app_with_temp_db: Any, tmp_path: Path) -> str:  # noqa: ARG001
    """Crée une ressource JSON locale et retourne son ID."""

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
