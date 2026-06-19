"""Tests de conformite a la terminologie CKAN opendata.swiss."""

from typing import cast

import pytest

from app.application.ports.ckan_payloads import (
    parse_package_payload,
    parse_package_search_response,
    parse_resource_payload,
)
from app.application.ports.ckan_types import (
    CkanPackagePayload,
    CkanPackageSearchResponse,
    CkanResourcePayload,
)


def _first_resource(parsed: CkanPackageSearchResponse) -> CkanResourcePayload:
    """Recupere la premiere ressource en validant les cles optionnelles attendues."""

    result = parsed.get("result")
    assert result is not None
    results = result.get("results")
    assert results is not None
    assert len(results) > 0

    resources = results[0].get("resources")
    assert resources is not None
    assert len(resources) > 0
    return resources[0]


def test_parse_package_search_supports_resource_distribution_fields() -> None:
    """Accepte package/dataset + resource/distribution avec les cles CKAN suisses."""

    payload: dict[str, object] = {
        "result": {
            "results": [
                {
                    "id": "dataset-solar-geneva",
                    "title": "Potentiel solaire geneve",
                    "organization": {"id": "org-geneve", "name": "etat-geneve"},
                    "resources": [
                        {
                            "id": "resource-geojson-1",
                            "package_id": "dataset-solar-geneva",
                            "download_url": "https://example.ch/solar.geojson",
                            "media-type": "GeoJSON",
                            "size": 1024,
                        }
                    ],
                }
            ]
        }
    }

    parsed = parse_package_search_response(cast(CkanPackageSearchResponse, payload))
    first_resource = _first_resource(parsed)

    assert first_resource.get("package_id") == "dataset-solar-geneva"
    assert first_resource.get("download_url") == "https://example.ch/solar.geojson"
    assert first_resource.get("url") == "https://example.ch/solar.geojson"
    assert first_resource.get("format") == "GeoJSON"


def test_parse_package_search_keeps_explicit_url_and_format() -> None:
    """Conserve la valeur explicite quand url/format sont deja fournis."""

    payload: dict[str, object] = {
        "result": {
            "results": [
                {
                    "id": "dataset-transport",
                    "title": "Transport public",
                    "resources": [
                        {
                            "id": "resource-csv-1",
                            "url": "https://example.ch/transport.csv",
                            "download_url": "https://mirror.example.ch/transport.csv",
                            "format": "CSV",
                            "media-type": "text/csv",
                        }
                    ],
                }
            ]
        }
    }

    parsed = parse_package_search_response(cast(CkanPackageSearchResponse, payload))
    first_resource = _first_resource(parsed)

    assert first_resource.get("url") == "https://example.ch/transport.csv"
    assert first_resource.get("format") == "CSV"


def test_parse_package_search_logs_and_skips_invalid_records(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Les enregistrements invalides sont journalises puis ignores."""

    payload: dict[str, object] = {
        "result": {
            "results": [
                {
                    "id": "dataset-valid",
                    "title": "Dataset valide",
                    "resources": [{"id": "r1", "download_url": "https://example.ch/r1.csv"}],
                },
                {
                    "id": 123,
                    "title": "Dataset invalide",
                },
            ]
        }
    }

    with caplog.at_level("WARNING"):
        parsed = parse_package_search_response(cast(CkanPackageSearchResponse, payload))

    result = parsed.get("result")
    assert result is not None
    results = result.get("results")
    assert results is not None
    assert len(results) == 1
    assert results[0].get("id") == "dataset-valid"
    assert "Record CKAN invalide ignore" in caplog.text


def test_parse_package_search_rejects_non_dict_payload() -> None:
    """Refuse une reponse racine non JSON object."""

    with pytest.raises(TypeError, match="response must be a JSON object"):
        parse_package_search_response("invalid")


def test_parse_package_search_rejects_invalid_result_shape() -> None:
    """Refuse un champ result non object et un results non array."""

    with pytest.raises(TypeError, match="result must be a JSON object"):
        parse_package_search_response({"result": "invalid"})

    with pytest.raises(TypeError, match="results must be a JSON array"):
        parse_package_search_response({"result": {"results": "invalid"}})


def test_parse_package_search_handles_missing_optional_nodes() -> None:
    """Tolere l'absence de result ou results et retourne une structure vide."""

    assert parse_package_search_response({}) == {}

    parsed = parse_package_search_response({"result": {}})
    result = parsed.get("result")
    assert result is not None
    assert result.get("results") is None


def test_parse_package_payload_rejects_non_list_tags_or_resources() -> None:
    """Refuse les structures tags/resources invalides."""

    with pytest.raises(TypeError, match="tags payload must be a JSON array"):
        parse_package_payload(cast(CkanPackagePayload, {"id": "d1", "tags": "invalid"}))

    with pytest.raises(TypeError, match="resources payload must be a JSON array"):
        parse_package_payload(cast(CkanPackagePayload, {"id": "d1", "resources": "invalid"}))


def test_parse_resource_payload_rejects_invalid_media_type_and_size() -> None:
    """Refuse media-type et size non conformes."""

    with pytest.raises(TypeError, match="field 'media-type' must be a string"):
        parse_resource_payload({"id": "r1", "media-type": 123})

    with pytest.raises(TypeError, match="resource size must be an integer"):
        parse_resource_payload({"id": "r1", "size": "invalid"})
