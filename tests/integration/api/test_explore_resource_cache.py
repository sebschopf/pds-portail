"""Tests de cache pour POST /resources/{id}/explore."""

from __future__ import annotations

from typing import Any, cast

from fastapi.testclient import TestClient
from httpx import Response

from app.infrastructure.persistence.models import LicenseModel


def test_explore_resource_cached_second_call(
    app_with_temp_db: Any,
    valid_license: LicenseModel,
    test_csv_resource: str,
    api_key: str,
) -> None:
    """Deux appels successifs retournent un cache hit au second passage."""

    assert valid_license is not None
    client = cast(Any, TestClient(app_with_temp_db))

    first_response = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": api_key},
        ),
    )
    second_response = cast(
        Response,
        client.post(
            f"/api/v1/resources/{test_csv_resource}/explore",
            headers={"X-API-Key": api_key},
        ),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_data = cast(dict[str, Any], first_response.json())
    second_data = cast(dict[str, Any], second_response.json())
    assert first_data["cached"] is False
    assert second_data["cached"] is True
    assert second_data["columns"] == first_data["columns"]
    assert second_data["analysis"] == first_data["analysis"]
