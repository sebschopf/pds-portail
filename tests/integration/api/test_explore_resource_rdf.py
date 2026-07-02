"""Tests RDF (Turtle, RDF/XML, JSON-LD) pour POST /resources/{id}/explore."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient
from httpx import Response

from app.domain.ckan_normalized import Dataset, NormalizedBatch, Organization, Resource
from app.infrastructure.persistence.models import LicenseModel

from ._fixtures import configure_api_modules


def test_explore_resource_turtle_returns_semantic_columns(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    tmp_path: Path,
    api_key: str,
) -> None:
    """POST /resources/{id}/explore Turtle valide → 200 + colonnes semantiques."""

    assert valid_license is not None
    ttl_path = tmp_path / "sample-resource.ttl"
    ttl_path.write_text(
        """
@prefix ex: <http://example.org/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:item1 a ex:Dataset ;
  rdfs:label "Population Geneve"@fr ;
  skos:broader ex:region1 ;
  ex:value "203856" .

ex:item2 a ex:Dataset ;
  rdfs:label "Population Lausanne"@fr ;
  ex:value "140202" .
""".strip(),
        encoding="utf-8",
    )

    _, cache_repository, _ = configure_api_modules()
    org = Organization(
        id="org-rdf",
        name="Observatoire RDF",
        description="Donnees semantiques",
        ckan_url="https://opendata.swiss/organization/observatoire-rdf",
        last_synced="2026-06-13T10:00:00Z",
    )
    dataset = Dataset(
        id="dataset-rdf",
        org_id="org-rdf",
        title="Concepts geographiques",
        description="Jeu de donnees RDF Turtle",
        tags=["rdf", "turtle"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=78,
        completeness=84,
        freshness_days=3,
        ckan_url="https://opendata.swiss/dataset/concepts-rdf",
    )
    resource = Resource(
        id="resource-rdf",
        dataset_id="dataset-rdf",
        name="Export Turtle",
        format="TTL",
        url=ttl_path.as_uri(),
        size_bytes=1500,
        created="2026-01-01T08:00:00Z",
        last_modified="2026-06-10T15:30:00Z",
    )
    cache_repository.upsert_normalized_batch(
        NormalizedBatch(organizations=[org], datasets=[dataset], resources=[resource])
    )

    client = cast(Any, TestClient(app_with_temp_db))
    response = cast(
        Response,
        client.post(
            "/api/v1/resources/resource-rdf/explore",
            headers={"X-API-Key": api_key},
        ),
    )

    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["format"] == "ttl"
    assert data["row_count"] >= 4
    names = [column["name"] for column in data["columns"]]
    assert "classes_count" in names
    assert "properties_count" in names
    assert "dominant_class" in names
    assert data["analysis"] is not None


def test_explore_resource_rdf_xml_returns_semantic_columns(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    tmp_path: Path,
    api_key: str,
) -> None:
    """POST /resources/{id}/explore RDF/XML valide → 200 + colonnes semantiques."""

    assert valid_license is not None
    rdf_xml_path = tmp_path / "sample-resource.rdf"
    rdf_xml_path.write_text(
        """
<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
  xmlns:ex="http://example.org/"
>
  <rdf:Description rdf:about="http://example.org/item1">
    <rdf:type rdf:resource="http://example.org/Dataset" />
    <rdfs:label xml:lang="fr">Population Geneve</rdfs:label>
    <ex:value>203856</ex:value>
  </rdf:Description>
  <rdf:Description rdf:about="http://example.org/item2">
    <rdf:type rdf:resource="http://example.org/Dataset" />
    <rdfs:label xml:lang="fr">Population Lausanne</rdfs:label>
    <ex:value>140202</ex:value>
  </rdf:Description>
</rdf:RDF>
""".strip(),
        encoding="utf-8",
    )

    _, cache_repository, _ = configure_api_modules()
    org = Organization(
        id="org-rdf-xml",
        name="Observatoire RDF XML",
        description="Donnees semantiques",
        ckan_url="https://opendata.swiss/organization/observatoire-rdf-xml",
        last_synced="2026-06-13T10:00:00Z",
    )
    dataset = Dataset(
        id="dataset-rdf-xml",
        org_id="org-rdf-xml",
        title="Concepts en RDF XML",
        description="Jeu de donnees RDF XML",
        tags=["rdf", "xml"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=76,
        completeness=82,
        freshness_days=4,
        ckan_url="https://opendata.swiss/dataset/concepts-rdf-xml",
    )
    resource = Resource(
        id="resource-rdf-xml",
        dataset_id="dataset-rdf-xml",
        name="Export RDF XML",
        format="RDF/XML",
        url=rdf_xml_path.as_uri(),
        size_bytes=1700,
        created="2026-01-01T08:00:00Z",
        last_modified="2026-06-10T15:30:00Z",
    )
    cache_repository.upsert_normalized_batch(
        NormalizedBatch(organizations=[org], datasets=[dataset], resources=[resource])
    )

    client = cast(Any, TestClient(app_with_temp_db))
    response = cast(
        Response,
        client.post(
            "/api/v1/resources/resource-rdf-xml/explore",
            headers={"X-API-Key": api_key},
        ),
    )

    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["format"] == "rdf/xml"
    assert data["row_count"] >= 1
    names = [column["name"] for column in data["columns"]]
    assert "classes_count" in names
    assert "language_count" in names
    assert data["analysis"] is not None


def test_explore_resource_json_ld_returns_semantic_columns(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    tmp_path: Path,
    api_key: str,
) -> None:
    """POST /resources/{id}/explore JSON-LD valide → 200 + colonnes semantiques."""

    assert valid_license is not None
    json_ld_path = tmp_path / "sample-resource.jsonld"
    json_ld_path.write_text(
        json.dumps(
            {
                "@context": {
                    "@vocab": "http://example.org/",
                    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                    "type": "@type",
                    "id": "@id",
                },
                "@graph": [
                    {
                        "id": "http://example.org/item1",
                        "type": "Dataset",
                        "rdfs:label": {"@value": "Population Geneve", "@language": "fr"},
                        "value": 203856,
                    },
                    {
                        "id": "http://example.org/item2",
                        "type": "Dataset",
                        "rdfs:label": {"@value": "Population Lausanne", "@language": "fr"},
                        "value": 140202,
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    _, cache_repository, _ = configure_api_modules()
    org = Organization(
        id="org-jsonld",
        name="Observatoire JSON-LD",
        description="Donnees semantiques",
        ckan_url="https://opendata.swiss/organization/observatoire-jsonld",
        last_synced="2026-06-13T10:00:00Z",
    )
    dataset = Dataset(
        id="dataset-jsonld",
        org_id="org-jsonld",
        title="Concepts en JSON-LD",
        description="Jeu de donnees JSON-LD",
        tags=["rdf", "json-ld"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=77,
        completeness=83,
        freshness_days=4,
        ckan_url="https://opendata.swiss/dataset/concepts-jsonld",
    )
    resource = Resource(
        id="resource-jsonld",
        dataset_id="dataset-jsonld",
        name="Export JSON-LD",
        format="JSON-LD",
        url=json_ld_path.as_uri(),
        size_bytes=1800,
        created="2026-01-01T08:00:00Z",
        last_modified="2026-06-10T15:30:00Z",
    )
    cache_repository.upsert_normalized_batch(
        NormalizedBatch(organizations=[org], datasets=[dataset], resources=[resource])
    )

    client = cast(Any, TestClient(app_with_temp_db))
    response = cast(
        Response,
        client.post(
            "/api/v1/resources/resource-jsonld/explore",
            headers={"X-API-Key": api_key},
        ),
    )

    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["format"] == "json-ld"
    assert data["row_count"] >= 1
    names = [column["name"] for column in data["columns"]]
    assert "properties_count" in names
    assert "has_hierarchy" in names
    assert data["analysis"] is not None
