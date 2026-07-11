"""Tests unitaires pour CkanNormalizer — branches défensives et normalisation."""

from __future__ import annotations

from app.domain.ckan_normalizer import (
    CkanNormalizer,
    _normalize_tag,
)  # noqa: PLC2701  # pyright: ignore[reportPrivateUsage]


class TestCkanNormalizer:
    """Tests pour la classe CkanNormalizer."""

    def test_normalize_ignores_dataset_sans_organisation(self) -> None:
        """Un dataset sans organisation est ignoré avec un warning (ligne 50-51)."""
        normalizer = CkanNormalizer(source="ckan")
        payload: dict[str, object] = {
            "result": {
                "results": [
                    {
                        "id": "ds-no-org",
                        "title": "Dataset sans org",
                        "notes": "Test",
                        "organization": None,
                        "tags": [],
                        "resources": [],
                    }
                ]
            }
        }
        batch = normalizer.normalize(payload)  # type: ignore[arg-type]
        assert len(batch.datasets) == 0
        assert len(batch.organizations) == 0

    def test_normalize_ignores_dataset_sans_id_ou_title(self) -> None:
        """Un dataset sans id ni title est ignoré avec un warning (lignes 68-70)."""
        normalizer = CkanNormalizer(source="ckan")
        payload: dict[str, object] = {
            "result": {
                "results": [
                    {
                        "id": None,
                        "title": None,
                        "notes": "Test",
                        "organization": {"id": "org-1", "name": "org"},
                        "tags": [],
                        "resources": [],
                    }
                ]
            }
        }
        batch = normalizer.normalize(payload)  # type: ignore[arg-type]
        assert len(batch.datasets) == 0

    def test_normalize_ignore_ressource_sans_id_ni_name(self) -> None:
        """Une ressource sans id ni name est ignorée (lignes 83-85)."""
        normalizer = CkanNormalizer(source="ckan")
        payload: dict[str, object] = {
            "result": {
                "results": [
                    {
                        "id": "ds-1",
                        "title": "Dataset valide",
                        "organization": {"id": "org-1", "name": "org"},
                        "tags": [],
                        "resources": [
                            {
                                "id": "res-ok",
                                "name": "Ressource valide",
                                "format": "CSV",
                            },
                            {
                                # Ressource sans id ni name — doit être ignorée
                                "format": "PDF",
                            },
                        ],
                    }
                ]
            }
        }
        batch = normalizer.normalize(payload)  # type: ignore[arg-type]
        # Une seule ressource conservée
        assert len(batch.resources) == 1
        assert batch.resources[0].id == "res-ok"

    def test_tag_value_returns_none_for_empty_tag_dict(self) -> None:
        """_tag_value retourne None quand le tag n'a ni display_name ni name (ligne 165)."""
        normalizer = CkanNormalizer()
        result = normalizer._tag_value({})  # pyright: ignore[reportPrivateUsage]
        assert result is None

    def test_tag_value_returns_none_for_falsy_value(self) -> None:
        """_tag_value retourne None quand la valeur normalisée est vide (ligne 182)."""
        normalizer = CkanNormalizer()
        result = normalizer._tag_value({"name": "   "})  # pyright: ignore[reportPrivateUsage]
        assert result is None

    def test_normalize_deduplicates_multilingual_tags(self) -> None:
        """Dédoublonne les tags multilingues après normalisation."""
        payload: dict[str, object] = {
            "result": {
                "results": [
                    {
                        "id": "ds-tags",
                        "title": "Tags test",
                        "organization": {"id": "org-1", "name": "org"},
                        "tags": [
                            {"name": "  MÉTÉO  "},
                            {"name": "meteo"},
                            {"display_name": "Météo"},
                        ],
                        "resources": [],
                    }
                ]
            }
        }
        normalizer = CkanNormalizer()
        batch = normalizer.normalize(payload)  # type: ignore[arg-type]
        assert len(batch.datasets) == 1
        assert batch.datasets[0].tags == ["meteo"]


class TestNormalizeTag:
    """Tests pour la fonction module _normalize_tag."""

    def test_returns_none_for_non_string(self) -> None:
        """_normalize_tag retourne None pour un int, dict, etc. (ligne 178)."""
        assert _normalize_tag(42) is None
        assert _normalize_tag({"fr": "test"}) is None
        assert _normalize_tag(None) is None

    def test_returns_none_for_empty_stripped(self) -> None:
        """_normalize_tag retourne None pour une chaîne vide après strip (lignes 182, 185)."""
        assert _normalize_tag("   ") is None
        assert _normalize_tag("") is None

    def test_normalizes_accented_tag(self) -> None:
        """Les accents sont supprimés via NFKD (ligne 183)."""
        result = _normalize_tag("Météo")
        assert result == "meteo"

    def test_collapses_multiple_spaces(self) -> None:
        """Les espaces multiples sont compactés (ligne 184)."""
        result = _normalize_tag("open    data")
        assert result == "open data"
