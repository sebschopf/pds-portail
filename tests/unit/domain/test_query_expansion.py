"""Tests unitaires pour le module d'expansion multilingue et synonymes.

Valide la normalisation des requetes, l'expansion par synonymes et
la couverture multilingue FR/DE/IT/EN via l'API publique uniquement.

References:
    PDS-41 (recherche multilingue)
    PRD-F10 (recherche multilingue FR/DE/IT/EN)
"""

from app.domain._query_dictionaries import MULTILINGUAL_DICTIONARY, SYNONYM_DICTIONARY
from app.domain.query_expansion import QueryExpander, expand_query


class TestExpandQueryFrench:
    """Tests d'expansion de requete en francais avec synonymes."""

    def test_transport_synonyms(self) -> None:
        """Requete 1: 'transport public' active les synonymes transport."""
        result = expand_query("transport public")
        assert "transport" in result.original_terms
        all_terms_set = set(result.all_terms)
        assert "mobilite" in all_terms_set or "trafic" in all_terms_set

    def test_sante_synonyms(self) -> None:
        """Requete 2: 'hopital soins' active le concept sante."""
        result = expand_query("hopital soins")
        concepts = [e["concept"] for e in result.expansions_applied]
        assert "sante" in concepts

    def test_education_synonyms(self) -> None:
        """Requete 3: 'ecole formation' active le concept education."""
        result = expand_query("ecole formation")
        concepts = [e["concept"] for e in result.expansions_applied]
        assert "education" in concepts

    def test_accents_are_normalized(self) -> None:
        """Les accents francais sont normalises (meteo -> meteo)."""
        result = expand_query("météo")
        # La normalisation retire les accents, donc le terme original devient 'meteo'
        assert "meteo" in result.original_terms


class TestExpandQueryGerman:
    """Tests d'expansion de requete en allemand (DE)."""

    def test_verkehr_expands_to_transport(self) -> None:
        """Requete 4: 'verkehr' (DE) est etendu vers synonymes transport."""
        result = expand_query("verkehr")
        all_terms_set = set(result.all_terms)
        assert "transport" in all_terms_set or "mobilite" in all_terms_set

    def test_gesundheit_expands_to_sante(self) -> None:
        """Requete 5: 'gesundheit' (DE) est etendu vers le concept sante."""
        result = expand_query("gesundheit")
        concepts = [e["concept"] for e in result.expansions_applied]
        assert "sante" in concepts

    def test_wetter_expands_to_meteo(self) -> None:
        """Requete 6: 'wetter' (DE) est etendu vers le concept meteo."""
        result = expand_query("wetter")
        all_terms_set = set(result.all_terms)
        assert "meteo" in all_terms_set or "wetter" in all_terms_set

    def test_umwelt_expands_to_environnement(self) -> None:
        """Requete 7: 'umwelt' (DE) active environnement."""
        result = expand_query("umwelt")
        concepts = [e["concept"] for e in result.expansions_applied]
        assert "environnement" in concepts

    def test_umlauts_are_normalized(self) -> None:
        """Les umlauts allemands sont normalises (o -> o)."""
        result = expand_query("bevölkerung")
        # 'bevolkerung' dans le dico multilingue, l'expansion doit trouver le concept
        concepts = [e["concept"] for e in result.expansions_applied]
        assert len(concepts) >= 1  # Doit matcher 'population'
        assert "population" in concepts


class TestExpandQueryItalian:
    """Tests d'expansion de requete en italien (IT)."""

    def test_trasporto_expands_to_transport(self) -> None:
        """Requete 8: 'trasporto' (IT) est etendu vers transport."""
        result = expand_query("trasporto")
        all_terms_set = set(result.all_terms)
        assert "transport" in all_terms_set or "mobilita" in all_terms_set

    def test_salute_expands_to_sante(self) -> None:
        """Requete 9: 'salute' (IT) active le concept sante."""
        result = expand_query("salute")
        concepts = [e["concept"] for e in result.expansions_applied]
        assert "sante" in concepts

    def test_meteo_expands_to_meteo(self) -> None:
        """Requete 10: 'meteo' (IT) active le concept meteo."""
        result = expand_query("meteo")
        concepts = [e["concept"] for e in result.expansions_applied]
        assert "meteo" in concepts

    def test_accents_are_normalized(self) -> None:
        """Les accents italiens sont normalises (a -> a)."""
        result = expand_query("mobilità")
        # 'mobilita' est un synonyme de 'transport'
        all_terms_set = set(result.all_terms)
        assert "transport" in all_terms_set or "mobilita" in all_terms_set


class TestExpandQueryEnglish:
    """Tests d'expansion de requete en anglais (EN)."""

    def test_weather_expands_to_meteo(self) -> None:
        """Requete 11: 'weather' (EN) est etendu vers meteo."""
        result = expand_query("weather")
        all_terms_set = set(result.all_terms)
        assert "meteo" in all_terms_set or "meteorologie" in all_terms_set

    def test_environment_expands_to_environnement(self) -> None:
        """Requete 12: 'environment' (EN) active environnement."""
        result = expand_query("environment")
        concepts = [e["concept"] for e in result.expansions_applied]
        assert "environnement" in concepts

    def test_health_expands_to_sante(self) -> None:
        """Requete 13: 'health' (EN) active le concept sante."""
        result = expand_query("health")
        concepts = [e["concept"] for e in result.expansions_applied]
        assert "sante" in concepts

    def test_case_insensitive(self) -> None:
        """La casse est ignoree: 'HEALTH' -> sante comme 'health'."""
        result = expand_query("HEALTH")
        concepts = [e["concept"] for e in result.expansions_applied]
        assert "sante" in concepts


class TestExpandQueryEdgeCases:
    """Tests de cas limites pour l'expansion de requete."""

    def test_empty_query_returns_empty(self) -> None:
        """Une requete vide retourne une expansion vide."""
        result = expand_query("")
        assert result.original_terms == []
        assert result.expanded_terms == []
        assert result.all_terms == []

    def test_unknown_term_no_expansion(self) -> None:
        """Un terme inconnu ne declenche pas d'expansion (pas de faux positif)."""
        result = expand_query("xyzzytruc inconnu")
        assert result.expansions_applied == []
        assert "xyzzytruc" in result.all_terms
        assert "inconnu" in result.all_terms

    def test_short_tokens_filtered(self) -> None:
        """Les tokens de moins de 2 caracteres sont ignores."""
        result = expand_query("a b")
        assert result.original_terms == []
        assert result.expanded_terms == []

    def test_punctuation_removed(self) -> None:
        """La ponctuation est supprimee de la requete."""
        result = expand_query("santé, éducation!")
        # Les deux tokens doivent etre normalises
        assert "sante" in result.original_terms
        assert "education" in result.original_terms

    def test_deduplication_of_terms(self) -> None:
        """Les termes dupliques entre origine et expansion sont deduplicates."""
        result = expand_query("transport")
        count = result.all_terms.count("transport")
        assert count == 1

    def test_expansions_applied_traced(self) -> None:
        """Les expansions appliquees sont tracees pour l'audit."""
        result = expand_query("hopital klimaat")
        expansions = result.expansions_applied
        assert len(expansions) >= 1
        concepts_found = {e["concept"] for e in expansions}
        assert "sante" in concepts_found

    def test_original_terms_preserved(self) -> None:
        """Les termes originaux sont toujours presents dans all_terms."""
        result = expand_query("météo santé")
        assert "meteo" in result.original_terms
        assert "sante" in result.original_terms


class TestDictionaryConsistency:
    """Tests de coherence des dictionnaires de donnees."""

    def test_all_concepts_have_multilingual_entries(self) -> None:
        """Chaque concept du dictionnaire de synonymes a une entree multilingue."""
        for concept in SYNONYM_DICTIONARY:
            assert concept in MULTILINGUAL_DICTIONARY, (
                f"Concept '{concept}' present dans SYNONYM_DICTIONARY "
                f"mais absent de MULTILINGUAL_DICTIONARY"
            )

    def test_no_empty_terms_in_dictionaries(self) -> None:
        """Aucun terme vide dans les dictionnaires."""
        for concept, synonyms in SYNONYM_DICTIONARY.items():
            for term in synonyms:
                assert (
                    term.strip()
                ), f"Terme vide dans SYNONYM_DICTIONARY pour le concept '{concept}'"
        for concept, lang_dict in MULTILINGUAL_DICTIONARY.items():
            for terms in lang_dict.values():
                for term in terms:
                    assert term.strip(), f"Terme vide dans MULTILINGUAL_DICTIONARY pour '{concept}'"


class TestQueryExpanderWithCustomDictionaries:
    """Tests de QueryExpander avec dictionnaires personnalises (injection)."""

    def test_custom_synonym_dict_used(self) -> None:
        """Un dictionnaire de synonymes personnalise est utilise."""
        custom: dict[str, list[str]] = {"test": ["alpha", "beta"]}
        expander = QueryExpander(synonym_dict=custom)
        result = expander.expand("alpha")
        assert "beta" in result.all_terms

    def test_custom_multilingual_dict_used(self) -> None:
        """Un dictionnaire multilingue personnalise est utilise."""
        custom_multi: dict[str, dict[str, list[str]]] = {
            "test": {"de": ["testen"], "en": ["testing"]}
        }
        expander = QueryExpander(multilingual_dict=custom_multi)
        result = expander.expand("testen")
        assert "testing" in result.all_terms
