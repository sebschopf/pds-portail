"""Tests unitaires des heuristiques d'analyse de ressource exploree."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.dataset_analyzer import analyse_explored_resource


@dataclass(slots=True)
class FakeColumnStats:
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None


@dataclass(slots=True)
class FakeColumn:
    name: str
    detected_type: str
    fill_rate: float
    sample_values: list[str]
    stats: FakeColumnStats | None = None


@dataclass(slots=True)
class FakeExploredResource:
    columns: list[FakeColumn]
    row_count: int


@dataclass(slots=True)
class FakeMetadata:
    dataset_title: str | None


def test_analyse_explored_resource_geo_temporal_numeric_returns_dashboard() -> None:
    """Geo + temporal + numeric → analyse de tableau de bord."""

    # Arrange : resource exploree avec signaux geo + temporal + numeric
    explored = FakeExploredResource(
        columns=[
            FakeColumn(
                name="commune",
                detected_type="string",
                fill_rate=1.0,
                sample_values=["Geneve", "Lausanne", "Berne"],
            ),
            FakeColumn(
                name="annee",
                detected_type="integer",
                fill_rate=1.0,
                sample_values=["2022", "2023", "2024"],
                stats=FakeColumnStats(min=2022.0, max=2024.0, mean=2023.0, median=2023.0),
            ),
            FakeColumn(
                name="population",
                detected_type="integer",
                fill_rate=1.0,
                sample_values=["203856", "140202", "134794"],
                stats=FakeColumnStats(
                    min=134794.0,
                    max=203856.0,
                    mean=159617.3,
                    median=140202.0,
                ),
            ),
        ],
        row_count=24,
    )

    # Act : analyser la structure detectee
    analysis = analyse_explored_resource(
        explored=explored,
        metadata=FakeMetadata(dataset_title="Population par commune"),
    )

    # Assert : l'analyse suggere un usage de pilotage geo-temporel
    assert "geographiques, temporelles et numeriques" in analysis.summary
    assert any("tableau de bord" in capability.lower() for capability in analysis.capabilities)
    assert any("tendances" in capability.lower() for capability in analysis.capabilities)


def test_analyse_explored_resource_sparse_rows_returns_caveats() -> None:
    """Lignes peu nombreuses et trous de donnees → caveats explicites."""

    # Arrange : resource partielle avec peu de lignes et un code exploitable
    explored = FakeExploredResource(
        columns=[
            FakeColumn(
                name="categorie",
                detected_type="string",
                fill_rate=0.6,
                sample_values=["bus", "tram"],
            ),
            FakeColumn(
                name="code",
                detected_type="string",
                fill_rate=1.0,
                sample_values=["A01", "A02"],
            ),
        ],
        row_count=3,
    )

    # Act : analyser la structure detectee
    analysis = analyse_explored_resource(
        explored=explored,
        metadata=FakeMetadata(dataset_title="Typologie de lignes"),
    )

    # Assert : l'analyse remonte les limites et le potentiel de jointure
    assert any("taux de remplissage faible" in caveat.lower() for caveat in analysis.caveats)
    assert any("peu de lignes" in caveat.lower() for caveat in analysis.caveats)
    assert any("aucune dimension temporelle" in caveat.lower() for caveat in analysis.caveats)
    assert any("croiser" in capability.lower() for capability in analysis.capabilities)


def test_analyse_explored_resource_temporal_numeric_returns_trend_and_stats() -> None:
    """Temporal + numeric → suivi chronologique et statistiques descriptives."""

    # Arrange : signaux temporels et numeriques sans dimension geo
    explored = FakeExploredResource(
        columns=[
            FakeColumn(
                name="annee",
                detected_type="integer",
                fill_rate=1.0,
                sample_values=["2021", "2022", "2023"],
                stats=FakeColumnStats(min=2021.0, max=2023.0, mean=2022.0, median=2022.0),
            ),
            FakeColumn(
                name="consommation",
                detected_type="float",
                fill_rate=1.0,
                sample_values=["24.1", "31.3", "42.0"],
                stats=FakeColumnStats(min=24.1, max=42.0, mean=32.46, median=31.3),
            ),
        ],
        row_count=12,
    )

    # Act : calcul de l'analyse
    analysis = analyse_explored_resource(
        explored=explored,
        metadata=FakeMetadata(dataset_title="Consommation annuelle"),
    )

    # Assert : suggestion chronologique et statistique presente
    assert "evolution temporelle" in analysis.summary.lower()
    assert any("evolution temporelle" in capability.lower() for capability in analysis.capabilities)
    assert any(
        "statistiques descriptives" in capability.lower() for capability in analysis.capabilities
    )
    assert not any("tableau de bord" in capability.lower() for capability in analysis.capabilities)


def test_analyse_explored_resource_categorical_returns_segmentation() -> None:
    """Colonne categorielle stable → suggestion de segmentation/filtrage."""

    # Arrange : signal categoriel avec faible cardinalite
    explored = FakeExploredResource(
        columns=[
            FakeColumn(
                name="categorie",
                detected_type="string",
                fill_rate=1.0,
                sample_values=["bus", "tram", "metro", "bus"],
            )
        ],
        row_count=40,
    )

    # Act : calcul de l'analyse
    analysis = analyse_explored_resource(
        explored=explored,
        metadata=FakeMetadata(dataset_title="Modes de transport"),
    )

    # Assert : capacite de segmentation activee
    assert any("segmenter" in capability.lower() for capability in analysis.capabilities)
