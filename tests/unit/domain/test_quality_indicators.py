"""Tests unitaires des regles d'indicateurs qualite dataset."""

from datetime import UTC, datetime

from app.domain.quality_indicators import (
    DatasetIndicatorInput,
    compute_freshness_days,
    compute_indicators,
)


def test_compute_freshness_days_parses_iso_zulu() -> None:
    """La fraicheur est calculee en jours sur une date ISO UTC."""

    reference_now = datetime(2026, 6, 13, 12, 0, tzinfo=UTC)
    assert compute_freshness_days("2026-06-10T09:30:00Z", now=reference_now) == 3


def test_compute_freshness_days_returns_none_for_invalid_date() -> None:
    """Une date invalide ne casse pas le calcul, elle est ignoree."""

    assert compute_freshness_days("not-a-date") is None


def test_compute_indicators_returns_stable_weighted_score() -> None:
    """Le score suit la formule ponderee sur 5 dimensions a 20 points."""

    input_data = DatasetIndicatorInput(
        description="Dataset transport urbain",
        tags=["mobilite", "geospatial"],
        created="2026-06-01T08:00:00Z",
        modified="2026-06-11T08:00:00Z",
        resource_formats=["CSV", "JSON"],
        resource_count=2,
    )

    indicators = compute_indicators(input_data, now=datetime(2026, 6, 13, 10, 0, tzinfo=UTC))

    assert indicators.completeness == 100
    assert indicators.freshness_days == 2
    assert indicators.quality_score == 90


def test_compute_indicators_handles_low_metadata_dataset() -> None:
    """Un dataset pauvre en metadata obtient un score faible mais stable."""

    input_data = DatasetIndicatorInput(
        description=None,
        tags=[],
        created=None,
        modified=None,
        resource_formats=[],
        resource_count=0,
    )

    indicators = compute_indicators(input_data, now=datetime(2026, 6, 13, 10, 0, tzinfo=UTC))

    assert indicators.completeness == 0
    assert indicators.freshness_days is None
    assert indicators.quality_score == 0


def test_compute_freshness_days_handles_empty_and_naive_datetime() -> None:
    """Gere les dates vides et les timestamps sans timezone."""

    assert compute_freshness_days("") is None

    reference_now = datetime(2026, 6, 13, 12, 0, tzinfo=UTC)
    assert compute_freshness_days("2026-06-10T09:30:00", now=reference_now) == 3


def test_compute_indicators_covers_intermediate_branches() -> None:
    """Couvre les branches intermediaires de fraicheur, formats et geotemporalite."""

    input_data = DatasetIndicatorInput(
        description="  ",
        tags=["mobilite"],
        created="2025-12-01T08:00:00Z",
        modified="2026-03-01T08:00:00Z",
        resource_formats=["XLS"],
        resource_count=3,
    )

    indicators = compute_indicators(input_data, now=datetime(2026, 6, 13, 10, 0, tzinfo=UTC))

    assert indicators.completeness == 80
    assert indicators.freshness_days == 104
    assert indicators.quality_score == 70


def test_compute_indicators_covers_empty_and_unknown_formats() -> None:
    """Couvre formats vides/inconnus et geotemporalite partielle."""

    input_data = DatasetIndicatorInput(
        description="description",
        tags=["geospatial"],
        created=None,
        modified=None,
        resource_formats=["   ", "BINARY"],
        resource_count=1,
    )

    indicators = compute_indicators(input_data, now=datetime(2026, 6, 13, 10, 0, tzinfo=UTC))

    assert indicators.completeness == 60
    assert indicators.freshness_days is None
    assert indicators.quality_score == 30
