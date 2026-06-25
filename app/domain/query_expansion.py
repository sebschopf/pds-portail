"""Expansion multilingue et synonymes metier pour la recherche dataset.

Encapsule la logique d'expansion de requete dans une classe QueryExpander
injectable, separant les donnees (dictionnaires) de la logique (expansion).

References:
    PRD-F01, PRD-F10 (recherche multilingue)
    PRD-NFR04 (accessibilite)
    ADR-003 (SRP/SOLID)
    ADR-023 (trajectoire M6)
    PDS-41 (tache de reference)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.domain._query_dictionaries import MULTILINGUAL_DICTIONARY, SYNONYM_DICTIONARY


@dataclass
class QueryExpansionResult:
    """Resultat de l'expansion d'une requete avec audit pour tracabilite.

    Attributes:
        original_terms: Termes originaux normalises de la requete utilisateur.
        expanded_terms: Termes ajoutes par expansion (synonymes + multilingues).
        all_terms: Liste dedupliquee et ordonnee (originaux puis expansions).
        expansions_applied: Trace des concepts actives, pour audit/debug.
    """

    original_terms: list[str]
    expanded_terms: list[str]
    all_terms: list[str] = field(init=False)
    expansions_applied: list[dict[str, str]]

    def __post_init__(self) -> None:
        """Deduplique et conserve l'ordre relatif (originaux puis expansions)."""
        seen: set[str] = set()
        ordered: list[str] = []
        for t in self.original_terms:
            if t and t not in seen:
                ordered.append(t)
                seen.add(t)
        for t in self.expanded_terms:
            if t and t not in seen:
                ordered.append(t)
                seen.add(t)
        self.all_terms = ordered


class QueryExpander:
    """Etend une requete utilisateur avec synonymes metier et equivalents multilingues.

    Responsabilite unique (SRP) : transformer une requete texte brute en un ensemble
    de termes etendus pour ameliorer le rappel de recherche multilingue.

    L'index inverse est construit au moment de l'instanciation a partir des
    dictionnaires injectables, ce qui permet le test et l'evolution independante.

    Usage:
        expander = QueryExpander()
        result = expander.expand("wetter")
        # result.all_terms contiendra ["wetter", "meteo", "meteorologie", ...]
    """

    def __init__(
        self,
        synonym_dict: dict[str, list[str]] | None = None,
        multilingual_dict: dict[str, dict[str, list[str]]] | None = None,
    ) -> None:
        """Initialise l'expander avec les dictionnaires fournis ou les defauts.

        Args:
            synonym_dict: Dictionnaire de synonymes FR (defaut: SYNONYM_DICTIONARY).
            multilingual_dict: Dictionnaire multilingue (defaut: MULTILINGUAL_DICTIONARY).
        """
        self._synonyms = synonym_dict if synonym_dict is not None else SYNONYM_DICTIONARY
        self._multilingual = (
            multilingual_dict if multilingual_dict is not None else MULTILINGUAL_DICTIONARY
        )
        self._reverse_index = self._build_reverse_index()

    def expand(self, query: str) -> QueryExpansionResult:
        """Etend une requete utilisateur avec synonymes metier et equivalents multilingues.

        Algorithme:
        1. Decoupage en termes normalises (minuscules, sans accents)
        2. Pour chaque terme, recherche dans l'index inverse
        3. Si un concept est trouve, ajoute les synonymes FR et equivalents DE/IT/EN
        4. Pas d'expansion pour les termes inconnus (pas de fausses associations)

        Args:
            query: Requete utilisateur brute (en francais, allemand, italien ou anglais).

        Returns:
            QueryExpansionResult contenant la liste de tous les termes pour la recherche.
        """
        # 1. Decoupage et normalisation
        original_terms = self._normalize_and_split(query)
        if not original_terms:
            return QueryExpansionResult(original_terms=[], expanded_terms=[], expansions_applied=[])

        # 2. Expansion par concept — chaque terme est recherche dans l'index inverse
        matched_concepts: set[str] = set()
        expansions_applied: list[dict[str, str]] = []

        for term in original_terms:
            concepts = self._reverse_index.get(term, [])
            for concept in concepts:
                if concept not in matched_concepts:
                    matched_concepts.add(concept)
                    expansions_applied.append({"term": term, "concept": concept})

        # 3. Collecte des termes etendus (synonymes FR + equivalents multilingues)
        expanded_terms: list[str] = []
        seen_expanded: set[str] = set(original_terms)

        for concept in matched_concepts:
            for syn in self._synonyms.get(concept, []):
                if syn not in seen_expanded:
                    expanded_terms.append(syn)
                    seen_expanded.add(syn)
            for lang_terms in self._multilingual.get(concept, {}).values():
                for t in lang_terms:
                    if t not in seen_expanded:
                        expanded_terms.append(t)
                        seen_expanded.add(t)

        return QueryExpansionResult(
            original_terms=original_terms,
            expanded_terms=expanded_terms,
            expansions_applied=expansions_applied,
        )

    # ------------------------------------------------------------------
    # Methodes privees
    # ------------------------------------------------------------------

    def _build_reverse_index(self) -> dict[str, list[str]]:
        """Construit l'index inverse terme -> [concepts] a partir des dictionnaires.

        Combine synonymes FR et equivalents multilingues en un seul index,
        en dedupliquant les concepts par terme. Les termes sont normalises
        (minuscules, sans accents) pour correspondre a la normalisation
        appliquee aux requetes utilisateur.

        Returns:
            Index inverse: cle = terme normalise, valeur = liste de concepts FR.
        """
        index: dict[str, set[str]] = {}
        for concept, synonyms in self._synonyms.items():
            for term in synonyms:
                normalized = self._normalize_term(term)
                if normalized:
                    index.setdefault(normalized, set()).add(concept)
        for concept, lang_dict in self._multilingual.items():
            for terms in lang_dict.values():
                for term in terms:
                    normalized = self._normalize_term(term)
                    if normalized:
                        index.setdefault(normalized, set()).add(concept)
        # Convertir les sets en listes triees pour la stabilite des tests
        return {term: sorted(concepts) for term, concepts in index.items()}

    @staticmethod
    def _normalize_term(term: str) -> str:
        """Normalise un terme isole du dictionnaire (minusc., sans accents).

        Args:
            term: Terme brut du dictionnaire.

        Returns:
            Terme normalise, ou chaine vide si le resultat fait moins de 2 caracteres.
        """
        text = term.lower().strip()
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        return text if len(text) >= 2 else ""

    @staticmethod
    def _normalize_and_split(text: str) -> list[str]:
        """Decoupe et normalise une chaine en termes de recherche.

        Supprime la ponctuation, passe en minuscules, retire les accents
        et filtre les tokens de moins de 2 caracteres.

        Args:
            text: Texte brut de la requete utilisateur.

        Returns:
            Liste de termes normalises (minuscules, sans accents, >= 2 caracteres).
        """
        text = text.lower().strip()
        # Supprimer les accents via decomposition Unicode
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        # Decouper sur les non-alphanumeriques
        tokens = re.split(r"[^a-z0-9]+", text)
        return [t.strip() for t in tokens if t.strip() and len(t.strip()) >= 2]


# Instance partagee par defaut pour usage interne au module
# (evite de reconstruire l'index a chaque appel)
_default_expander = QueryExpander()


def expand_query(query: str) -> QueryExpansionResult:
    """Fonction de commodite utilisant l'instance partagee par defaut.

    Args:
        query: Requete utilisateur brute.

    Returns:
        QueryExpansionResult contenant la liste de tous les termes pour la recherche.
    """
    return _default_expander.expand(query)
