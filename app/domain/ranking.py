"""Ranking hybride explicable pour la recherche dataset.

Combine trois signaux — pertinence textuelle, qualite dataset et fraicheur —
en un score pondere unique, avec exposition des composantes pour le frontend.

References:
    PRD-F01, PRD-F02, PRD-F09 (pertinence utile)
    ADR-003, ADR-004, ADR-023 (architecture scoring)
    SPEC-002 (indicateurs qualite)
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp

# --- Poids par defaut documentes ---
# Justification produit :
# - Texte (0.50) : la pertinence semantique doit etre le signal principal
# - Qualite (0.30) : la fiabilite metadata est un critere discriminant fort
# - Fraicheur (0.20) : la recence est importante mais pas dominante
# Ces valeurs sont versionnees et evolueront avec les retours utilisateurs (M7).

DEFAULT_WEIGHT_TEXT = 0.50
DEFAULT_WEIGHT_QUALITY = 0.30
DEFAULT_WEIGHT_FRESHNESS = 0.20

# Fraicheur : facteur d'echelle du decay exponentiel.
# A 90 jours, la composante vaut exp(-1) ≈ 0.3679.
FRESHNESS_DECAY_SCALE_DAYS = 90


@dataclass(frozen=True, slots=True)
class HybridRankingWeights:
    """Poids documentes de chaque composante du ranking hybride."""

    text: float = DEFAULT_WEIGHT_TEXT
    quality: float = DEFAULT_WEIGHT_QUALITY
    freshness: float = DEFAULT_WEIGHT_FRESHNESS

    def __post_init__(self) -> None:
        """Valide que les poids sont positifs et somment a 1.0."""
        total = self.text + self.quality + self.freshness
        if not (0.99 < total < 1.01):
            msg = (
                f"Les poids doivent sommer a 1.0 (actuel: {total:.4f}). "
                f"text={self.text}, quality={self.quality}, freshness={self.freshness}"
            )
            raise ValueError(msg)
        for name, value in [
            ("text", self.text),
            ("quality", self.quality),
            ("freshness", self.freshness),
        ]:
            if value < 0 or value > 1:
                msg = f"Le poids '{name}' doit etre entre 0 et 1 (recu: {value})"
                raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class HybridRankingSignals:
    """Signaux exposes a l'API et au frontend pour expliquer le classement.

    Chaque composante est sur [0, 1] et represente la contribution avant ponderation.
    """

    hybrid_score: float = 0.0  # Score final combine sur [0, 1]
    text_score: float = 0.0  # Pertinence textuelle (TF/IDF simplifiee) sur [0, 1]
    quality_normalized: float = 0.0  # Score qualite normalise sur [0, 1]
    freshness_component: float = 0.0  # Composante fraicheur sur [0, 1]
    weight_text: float = DEFAULT_WEIGHT_TEXT  # Poids applique a la composante texte
    weight_quality: float = DEFAULT_WEIGHT_QUALITY  # Poids applique a la composante qualite
    weight_freshness: float = DEFAULT_WEIGHT_FRESHNESS  # Poids applique a la composante fraicheur

    def to_dict(self) -> dict[str, float]:
        """Retourne les signaux sous forme dictionnaire pour serialisation API."""
        return {
            "hybrid_score": round(self.hybrid_score, 4),
            "text_score": round(self.text_score, 4),
            "quality_normalized": round(self.quality_normalized, 4),
            "freshness_component": round(self.freshness_component, 4),
            "weight_text": self.weight_text,
            "weight_quality": self.weight_quality,
            "weight_freshness": self.weight_freshness,
        }


def compute_text_score(query_terms: list[str], title: str, description: str | None) -> float:
    """Calcule un score de pertinence textuelle simplifie sur [0, 1].

    Approche de rappel simplifiee :
    - Compte les termes du query presents dans le titre ou la description
    - Normalise par le nombre total de termes
    - Retourne 0.0 si query vide ou sans match

    Args:
        query_terms: Termes de la requete (en minuscules)
        title: Titre du dataset
        description: Description du dataset (optionnelle)

    Returns:
        Score entre 0 et 1
    """
    if not query_terms:
        return 0.0

    title_lower = (title or "").lower()
    desc_lower = (description or "").lower()

    matched_score = 0.0
    for term in query_terms:
        term_lower = term.lower()
        term_matches = 0
        if term_lower in title_lower:
            term_matches += 1
        if term_lower in desc_lower:
            term_matches += 1
        matched_score += 1.0 if term_matches > 0 else 0.0

    return matched_score / len(query_terms)


def compute_freshness_component(freshness_days: int | None) -> float:
    """Calcule la composante fraicheur sur [0, 1] par decay exponentiel.

    Formule : exp(-freshness_days / decay_scale)
    - 0 jour → 1.0
    - 90 jours → ~0.3679
    - 365 jours → ~0.017

    Args:
        freshness_days: Jours depuis derniere MAJ (None si inconnu)

    Returns:
        Score entre 0 et 1
    """
    if freshness_days is None or freshness_days < 0:
        return 0.0
    return exp(-freshness_days / FRESHNESS_DECAY_SCALE_DAYS)


def compute_hybrid_score(
    quality_score: int | None,
    freshness_days: int | None,
    query_terms: list[str],
    title: str,
    description: str | None,
    weights: HybridRankingWeights | None = None,
) -> HybridRankingSignals:
    """Calcule le score hybride final et expose les composantes.

    Le score combine pondere :
    1. text_score (poids texte) : pertinence title/description
    2. quality_normalized (poids qualite) : quality_score / 100
    3. freshness_component (poids fraicheur) : decay exponentiel

    Args:
        quality_score: Score qualite 0-100 (None si non calcule)
        freshness_days: Jours depuis derniere MAJ (None si inconnu)
        query_terms: Termes de la requete normalises
        title: Titre du dataset
        description: Description du dataset
        weights: Poids optionnels (utilise les defauts si None)

    Returns:
        HybridRankingSignals avec score final et composantes
    """
    w = weights or HybridRankingWeights()

    text_score = compute_text_score(query_terms, title, description)
    quality_normalized = (quality_score or 0) / 100.0
    freshness_component = compute_freshness_component(freshness_days)

    hybrid_score = (
        w.text * text_score + w.quality * quality_normalized + w.freshness * freshness_component
    )

    return HybridRankingSignals(
        hybrid_score=hybrid_score,
        text_score=text_score,
        quality_normalized=quality_normalized,
        freshness_component=freshness_component,
        weight_text=w.text,
        weight_quality=w.quality,
        weight_freshness=w.freshness,
    )
