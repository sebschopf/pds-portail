"""Tests tabulaires CSV/JSON pour POST /resources/{id}/explore."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient
from httpx import Response

from app.domain.ckan_normalized import Dataset, NormalizedBatch, Organization, Resource
from app.infrastructure.persistence.models import LicenseModel

from ._fixtures import configure_api_modules


def test_explore_resource_success_csv(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    test_csv_resource: str,
    api_key: str,
) -> None:
    """POST /resources/{id}/explore CSV valide → 200 + structure + analyse."""

    assert valid_license is not None
    client = cast(Any, TestClient(app_with_temp_db))
    response = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": api_key},
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
    assert data["analysis"]["summary"] == (
        "Donnees de mobilite urbaine contient des mesures numeriques rattachees a des territoires."
    )
    assert any("carte" in capability.lower() for capability in data["analysis"]["capabilities"])
    assert any("heuristique" in caveat.lower() for caveat in data["analysis"]["caveats"])


def test_explore_resource_success_json(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    test_json_resource: str,
    api_key: str,
) -> None:
    """POST /resources/{id}/explore JSON valide → 200 + structure analysee."""

    assert valid_license is not None
    client = cast(Any, TestClient(app_with_temp_db))
    response = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_json_resource}/explore",
            headers={"X-API-Key": api_key},
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
    assert "territoires" in data["analysis"]["summary"].lower()
    assert len(data["analysis"]["capabilities"]) >= 2


def test_explore_resource_malformed_json_returns_422(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    tmp_path: Path,
    api_key: str,
) -> None:
    """JSON invalide → 422 avec une erreur de parsing propre."""

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
            headers={"X-API-Key": api_key},
        ),
    )

    assert response.status_code == 422
    assert "Failed to parse resource" in response.json()["detail"]
