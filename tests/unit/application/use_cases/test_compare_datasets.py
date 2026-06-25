"""Tests unitaires pour CompareDatasetsUseCase (PDS-43)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.application.use_cases.compare_datasets import (
    CompareDatasetsUseCase,
    InvalidCompareRequestError,
)
from app.presentation.api.v1.schemas import (
    MAX_COMPARE_IDS,
    CompareItem,
    CompareRequest,
    CompareResponse,
)


class FakeCompareRepo:
    """Repository factice pour les tests de CompareDatasetsUseCase.

    Precondition: la methode get_by_ids doit preserver l'ordre des IDs
    demandes (comme l'implementation reelle SqlAlchemySearchRepository).
    """

    def __init__(self, items: list[CompareItem] | None = None) -> None:
        self._items = items or []
        self._called_with: list[list[str]] = []

    def get_by_ids(self, ids: list[str]) -> list[CompareItem]:
        self._called_with.append(ids)
        # Preserver l'ordre des IDs demandes (comme l'implementation reelle)
        ds_map = {item.id: item for item in self._items}
        return [ds_map[id_] for id_ in ids if id_ in ds_map]


def _make_item(id_: str, title: str = "") -> CompareItem:
    return CompareItem(
        id=id_,
        title=title or f"Dataset {id_}",
        org_name="Org Test",
        description="Description test.",
        license="CC-BY 4.0",
        quality_score=75,
        completeness=80,
        freshness_days=30,
        resource_formats=["CSV", "JSON"],
        resource_count=3,
        tags=["test", "comparaison"],
        ckan_url=None,
    )


class TestCompareDatasetsUseCase:
    """Tests pour le cas d'usage de comparaison guidee."""

    def test_execute_2_ids(self) -> None:
        """2 IDs valides retournent 2 items."""
        items = [_make_item("a"), _make_item("b")]
        repo = FakeCompareRepo(items)
        uc = CompareDatasetsUseCase(repo)

        result = uc.execute(CompareRequest(ids=["a", "b"]))
        assert isinstance(result, CompareResponse)
        assert len(result.items) == 2

    def test_execute_4_ids(self) -> None:
        """4 IDs valides sont acceptes (max)."""
        items = [_make_item("a"), _make_item("b"), _make_item("c"), _make_item("d")]
        repo = FakeCompareRepo(items)
        uc = CompareDatasetsUseCase(repo)

        result = uc.execute(CompareRequest(ids=["a", "b", "c", "d"]))
        assert len(result.items) == 4

    def test_execute_with_blank_ids(self) -> None:
        """Les IDs vides ou blancs sont ignores dans le use case."""
        items = [_make_item("a"), _make_item("b")]
        repo = FakeCompareRepo(items)
        uc = CompareDatasetsUseCase(repo)

        result = uc.execute(CompareRequest(ids=["a", "b", "  ", ""]))
        assert len(result.items) == 2

    def test_rejects_1_id(self) -> None:
        """Moins de 2 IDs dans la requete leve ValidationError Pydantic."""
        with pytest.raises(PydanticValidationError, match=r"(too_short|Au moins)"):
            CompareRequest(ids=["a"])

    def test_rejects_more_than_max(self) -> None:
        """Plus de MAX_COMPARE_IDS leve ValidationError Pydantic."""
        ids = [f"id_{i}" for i in range(MAX_COMPARE_IDS + 2)]
        with pytest.raises(PydanticValidationError, match=r"(too_long|Maximum)"):
            CompareRequest(ids=ids)

    def test_rejects_when_fewer_than_2_valid_in_db(self) -> None:
        """Si la DB ne retourne que 1 item sur 2 demandes, erreur."""
        items = [_make_item("a")]
        repo = FakeCompareRepo(items)
        uc = CompareDatasetsUseCase(repo)

        with pytest.raises(InvalidCompareRequestError, match="Au moins 2"):
            uc.execute(CompareRequest(ids=["a", "b"]))

    def test_preserves_order(self) -> None:
        """L'ordre des items suit l'ordre des IDs de la requete."""
        items = [_make_item("c"), _make_item("a"), _make_item("b")]
        repo = FakeCompareRepo(items)
        uc = CompareDatasetsUseCase(repo)

        result = uc.execute(CompareRequest(ids=["a", "c"]))
        ids_out = [item.id for item in result.items]
        assert ids_out == ["a", "c"], f"Ordre attendu [a, c], recu {ids_out}"

    def test_silently_skips_missing_ids(self) -> None:
        """Les IDs inexistants en DB sont ignores sans erreur (tant qu'il reste >=2)."""
        items = [_make_item("a"), _make_item("b")]
        repo = FakeCompareRepo(items)
        uc = CompareDatasetsUseCase(repo)

        result = uc.execute(CompareRequest(ids=["a", "z", "b", "y"]))
        assert len(result.items) == 2
        assert {item.id for item in result.items} == {"a", "b"}

    def test_id_strips_whitespace(self) -> None:
        """Les espaces autour des IDs sont elimines."""
        items = [_make_item("a"), _make_item("b")]
        repo = FakeCompareRepo(items)
        uc = CompareDatasetsUseCase(repo)

        result = uc.execute(CompareRequest(ids=["  a  ", " b "]))
        assert len(result.items) == 2
