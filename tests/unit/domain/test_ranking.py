"""Tests unitaires du ranking hybride explicable.

Couvre :
- compute_text_score : cas nominal, query vide, presence titre/description
- compute_freshness_component : decay exponentiel, None, negatif
- HybridRankingWeights : validation des poids
- compute_hybrid_score : integration des 3 composantes, non-regression
"""

from math import exp

import pytest

from app.domain.ranking import (
    DEFAULT_WEIGHT_FRESHNESS,
    DEFAULT_WEIGHT_QUALITY,
    DEFAULT_WEIGHT_TEXT,
    HybridRankingSignals,
    HybridRankingWeights,
    compute_freshness_component,
    compute_hybrid_score,
    compute_text_score,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _almost_equal(a: float, b: float, eps: float = 1e-6) -> bool:
    return abs(a - b) < eps


# ── Tests compute_text_score ────────────────────────────────────────


class TestComputeTextScore:
    def test_query_vide_retourne_zero(self) -> None:
        assert compute_text_score([], "Titre", "Desc") == 0.0

    def test_match_titre_seul(self) -> None:
        score = compute_text_score(["population"], "Population Geneve", "Donnees demographiques")
        assert score == 1.0  # le terme est dans le titre → match

    def test_match_description_seule(self) -> None:
        score = compute_text_score(["donnees"], "Population Geneve", "Donnees demographiques")
        assert score == 1.0  # le terme est dans la description → match

    def test_match_titre_et_description(self) -> None:
        score = compute_text_score(
            ["geneve"], "Population Geneve", "Donnees demographiques genevoises"
        )
        assert score == 1.0  # dans titre + description, mais toujours 1.0

    def test_aucun_match(self) -> None:
        score = compute_text_score(["meteo"], "Population Geneve", "Donnees demographiques")
        assert score == 0.0

    def test_match_partiel_sur_plusieurs_termes(self) -> None:
        score = compute_text_score(
            ["population", "meteo"], "Population Geneve", "Donnees demographiques"
        )
        assert _almost_equal(score, 0.5)  # 1/2 termes

    def test_case_insensitive(self) -> None:
        score = compute_text_score(["POPULATION"], "population geneve", "desc")
        assert score == 1.0

    def test_insensibilite_aux_accents_simple(self) -> None:
        # Le ranking actuel ne gere pas les accents, mais ne doit pas planter
        score = compute_text_score(["genève"], "Population Geneve", "desc")
        assert score == 0.0  # pas de match accentué → OK

    def test_description_none_graceful(self) -> None:
        score = compute_text_score(["geneve"], "Population Geneve", None)
        assert score == 1.0


# ── Tests compute_freshness_component ───────────────────────────────


class TestComputeFreshnessComponent:

    def test_zero_jour_retourne_un(self) -> None:
        assert compute_freshness_component(0) == 1.0

    def test_decay_scale_donne_exp_minus_1(self) -> None:
        expected = exp(-1.0)  # -90/90 = -1
        assert _almost_equal(compute_freshness_component(90), expected)

    def test_inconnu_retourne_zero(self) -> None:
        assert compute_freshness_component(None) == 0.0

    def test_negatif_retourne_zero(self) -> None:
        assert compute_freshness_component(-5) == 0.0

    def test_tres_vieux_approach_zero(self) -> None:
        score = compute_freshness_component(365 * 10)  # 10 ans
        assert score < 0.01


# ── Tests HybridRankingWeights ──────────────────────────────────────


class TestHybridRankingWeights:
    def test_poids_defauts(self) -> None:
        w = HybridRankingWeights()
        assert _almost_equal(w.text, DEFAULT_WEIGHT_TEXT)
        assert _almost_equal(w.quality, DEFAULT_WEIGHT_QUALITY)
        assert _almost_equal(w.freshness, DEFAULT_WEIGHT_FRESHNESS)
        assert _almost_equal(w.text + w.quality + w.freshness, 1.0)

    def test_poids_somme_inferieure_leve_exception(self) -> None:
        with pytest.raises(ValueError, match="doivent sommer a 1.0"):
            HybridRankingWeights(text=0.3, quality=0.3, freshness=0.3)

    def test_poids_somme_superieure_leve_exception(self) -> None:
        with pytest.raises(ValueError, match="doivent sommer a 1.0"):
            HybridRankingWeights(text=0.6, quality=0.3, freshness=0.2)

    def test_poids_hors_0_1_leve_exception(self) -> None:
        with pytest.raises(ValueError, match="doit etre entre 0 et 1"):
            HybridRankingWeights(text=1.5, quality=0.3, freshness=-0.8)


# ── Tests integration compute_hybrid_score ──────────────────────────


class TestComputeHybridScore:
    def test_retourne_HybridRankingSignals(self) -> None:
        result = compute_hybrid_score(
            quality_score=80,
            freshness_days=10,
            query_terms=["population"],
            title="Population Geneve",
            description="Donnees demographiques sur Geneve",
        )
        assert isinstance(result, HybridRankingSignals)

    def test_composantes_dans_0_1(self) -> None:
        result = compute_hybrid_score(
            quality_score=75,
            freshness_days=30,
            query_terms=["population", "geneve"],
            title="Population Geneve 2024",
            description=None,
        )
        assert 0.0 <= result.text_score <= 1.0
        assert 0.0 <= result.quality_normalized <= 1.0
        assert 0.0 <= result.freshness_component <= 1.0
        assert 0.0 <= result.hybrid_score <= 1.0

    def test_hybrid_score_bon_texte_qualite_fraicheur(self) -> None:
        """Cas nominal : tous les signaux sont forts."""
        result = compute_hybrid_score(
            quality_score=90,
            freshness_days=5,
            query_terms=["population"],
            title="Population Suisse 2024",
            description="Statistiques demographiques de la population suisse",
        )
        # text_score = 1.0 (terme dans titre), quality = 0.9, freshness ≈ 0.95
        expected = 0.5 * 1.0 + 0.3 * 0.9 + 0.2 * exp(-5 / 90)
        assert _almost_equal(result.hybrid_score, expected)

    def test_hybrid_score_mauvais_signaux(self) -> None:
        """Cas defavorable : texte hors-sujet, qualite nulle, jamais mis a jour."""
        result = compute_hybrid_score(
            quality_score=0,
            freshness_days=None,  # fraicheur inconnue → 0
            query_terms=["meteo"],
            title="Population Geneve",
            description="Donnees purement demographiques",
        )
        # text_score = 0.0 (pas de match), quality = 0.0, freshness = 0.0
        assert _almost_equal(result.hybrid_score, 0.0)

    def test_poids_personnalises(self) -> None:
        """Verifie que des poids custom modifient le score final."""
        poids_qualite_max = HybridRankingWeights(text=0.0, quality=1.0, freshness=0.0)
        result = compute_hybrid_score(
            quality_score=50,
            freshness_days=999,
            query_terms=["meteo"],
            title="Meteo Suisse",
            description=None,
            weights=poids_qualite_max,
        )
        # Avec poids qualite=1, le resultat = 0.5
        assert _almost_equal(result.hybrid_score, 0.5)
        assert _almost_equal(result.weight_quality, 1.0)

    def test_to_dict_expose_tous_les_champs(self) -> None:
        result = compute_hybrid_score(
            quality_score=80,
            freshness_days=10,
            query_terms=["test"],
            title="Test dataset",
            description="Un dataset de test",
        )
        d = result.to_dict()
        expected_keys = {
            "hybrid_score",
            "text_score",
            "quality_normalized",
            "freshness_component",
            "weight_text",
            "weight_quality",
            "weight_freshness",
        }
        assert set(d.keys()) == expected_keys
        for key in expected_keys:
            assert isinstance(d[key], float)

    def test_query_vide_produit_ranking_signaux_mais_texte_zero(self) -> None:
        """Sans termes de requete, text_score = 0 mais les signaux existent."""
        result = compute_hybrid_score(
            quality_score=80,
            freshness_days=10,
            query_terms=[],
            title="Population Geneve",
            description="Desc",
        )
        assert _almost_equal(result.text_score, 0.0)
        assert result.hybrid_score > 0  # qualite + fraicheur contribuent encore

    def test_non_regression_score_stable(self) -> None:
        """Garantit que le score est stable a 1e-6 pres sur un cas de reference."""
        result = compute_hybrid_score(
            quality_score=85,
            freshness_days=15,
            query_terms=["population", "suisse"],
            title="Population Suisse 2024",
            description="Statistiques officielles de la population suisse",
        )
        # Valeur calculee manuellement pour non-regression
        text = 1.0  # les 2 termes sont dans le titre
        quality = 0.85
        fresh = exp(-15 / 90)
        expected = 0.5 * text + 0.3 * quality + 0.2 * fresh
        assert _almost_equal(result.hybrid_score, expected)
