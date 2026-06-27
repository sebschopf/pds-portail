# SPEC-003 : Recherche multilingue et synonymes métier

> Trace de traçabilité : couvre **SPEC-F06** (PRD-F10)

## Identification

| Propriété           | Valeur                                               |
|---------------------|------------------------------------------------------|
| **Titre**           | Recherche multilingue FR/DE/IT/EN et synonymes métier |
| **Version**         | 0.2 (Active)                                         |
| **Date**            | 2026-06-27                                           |
| **Auteur**          | mous_tik                                             |
| **Statut**          | Active                                               |
| **Phase du projet** | Technique                                            |
| **SPEC couverte**   | SPEC-F06                                             |

---

## 1. Objectif

Améliorer le rappel de la recherche sans dégrader la précision, en couvrant les variantes linguistiques (français, allemand, italien, anglais) et un premier dictionnaire de synonymes métier orientés usages publics suisses.

Exigences couvertes :
- PRD-F01 / SPEC-F01 (recherche facettée avec pertinence)
- PRD-F10 / SPEC-F06 (recherche multilingue et synonymes métier)
- PRD-NFR04 (accessibilité des résultats)

---

## 2. Données d'entrée

La normalisation s'applique à la **requête utilisateur brute** avant son passage dans le pipeline de recherche SQLite.

Deux dictionnaires statiques versionnés sont utilisés :

| Dictionnaire | Contenu | Emplacement |
|---|---|---|
| Synonymes FR | 15 concepts métier (transport, santé, éducation, etc.) | `app/domain/_query_dictionaries.py::SYNONYM_DICTIONARY` |
| Multilingue | 20 concepts × 4 langues (FR/DE/IT/EN) | `app/domain/_query_dictionaries.py::MULTILINGUAL_DICTIONARY` |

Les dictionnaires sont maintenus manuellement et audités en CI via des tests de cohérence (`test_query_expansion.py::TestDictionaryConsistency`).

---

## 3. Algorithme d'expansion

L'expansion est effectuée par la classe `QueryExpander` (`app/domain/query_expansion.py`).

### 3.1 Normalisation de la requête

```
requête brute → minuscules → suppression accents (NFKD/ASCII) → découpage tokens ≥ 2 caractères
```

Exemples :
- `"météo"` → `["meteo"]`
- `"bevölkerung"` → `["bevolkerung"]`
- `"TRANSPORT Public"` → `["transport", "public"]`

### 3.2 Résolution par index inverse

Un index inverse (terme → [concepts]) est construit au `__init__` à partir des deux dictionnaires, avec normalisation identique (termes sans accents, minuscules).

Pour chaque terme de la requête :
1. Recherche dans l'index inverse
2. Si le terme matche un ou plusieurs concepts, ces concepts sont activés
3. Les synonymes FR et équivalents multilingues de chaque concept activé sont ajoutés à la requête étendue

### 3.3 Traçabilité

Chaque résultat d'expansion (`QueryExpansionResult`) expose :
- `original_terms` : termes originaux normalisés
- `expanded_terms` : termes ajoutés par expansion
- `all_terms` : liste dédupliquée (originaux puis expansions)
- `expansions_applied` : liste des mappings terme → concept, pour audit

### 3.4 Intégration au pipeline de recherche

L'expansion est injectée dans `SqlAlchemySearchRepository.search()` au niveau de la clause WHERE :

```
expansion = expand_query(query)
→ pour chaque terme dans all_terms : LIKE %terme% sur title / description / org_name / tags
→ OR logique entre les termes
→ fallback LIKE %query% si aucun concept reconnu
```

**Limite anti-explosion (PDS-70)** : `MAX_EXPANSION_TERMS = 12`. Quand l'utilisateur combine plusieurs mots-clés (ex: "mobilité économie santé"), l'expansion peut générer 50+ termes (3 concepts × ~20 termes/concept). La limite à 12 empêche l'explosion combinatoire des clauses LIKE (> 200 LIKE → timeout SQLite). Les termes originaux de l'utilisateur sont toujours prioritaires (placés en tête de `all_terms`).

### 3.5 Index FTS5 avec suppression automatique des diacritiques (PDS-70)

En complément de l'expansion de requête, la table FTS5 `datasets_fts` utilise le tokenizer `unicode61 remove_diacritics 2` qui supprime automatiquement les accents (FR/DE/IT) sans avoir besoin d'appeler `func.replace()` en SQL. Trois triggers AFTER INSERT/UPDATE/DELETE sur `datasets` maintiennent l'index à jour, et un backfill initial est exécuté au `create_schema()`.

---

## 4. Comportement attendu

### 4.1 Requêtes intra-langue (synonymes)

| Requête utilisateur | Termes étendus (extrait) | Effet |
|---|---|---|
| `"transport"` | + `mobilite`, `trafic`, `verkehr`, `mobility` | Rappel élargi sur le concept transport |
| `"hopital"` | + `sante`, `medical`, `gesundheit`, `health` | Un dataset taggé `gesundheit` est trouvé |

### 4.2 Requêtes cross-langue

| Langue | Requête | Concept activé | Termes FR ajoutés |
|---|---|---|---|
| DE | `"wetter"` | meteo | `meteo`, `meteorologie`, `weather` |
| IT | `"trasporto"` | transport | `transport`, `mobilite`, `trafic` |
| EN | `"health"` | sante | `sante`, `hopital`, `medical` |

### 4.3 Termes inconnus

Un terme absent des dictionnaires (ex: `"xyzzytruc"`) ne déclenche **aucune expansion** — il est conservé tel quel dans `all_terms`. Pas de faux positif.

---

## 5. Contrats API

### 5.1 Fonction publique

```python
def expand_query(query: str) -> QueryExpansionResult
```

Instance par défaut de `QueryExpander` construite avec les dictionnaires de production.

### 5.2 Classe injectable (pour tests)

```python
class QueryExpander:
    def __init__(
        self,
        synonym_dict: dict[str, list[str]] | None = None,
        multilingual_dict: dict[str, dict[str, list[str]]] | None = None,
    ) -> None: ...

    def expand(self, query: str) -> QueryExpansionResult: ...
```

---

## 6. Limites connues

| Limite | Impact | Plan d'amélioration |
|---|---|---|
| ~30 concepts couverts | Les requêtes hors concepts connus ne bénéficient pas d'expansion | Enrichissement itératif via retours utilisateurs (M7) |
| Pas de stemming / lemmatisation | `"écoles"` ne matche pas `"école"` sauf si les deux sont dans le dictionnaire | Ajout d'un stemmer léger si le besoin est confirmé |
| Pas de pondération des termes étendus | Tous les termes ont le même poids dans le LIKE | Possibilité d'ajouter des poids aux synonymes dans une V2 |
| Expansion au niveau SQL uniquement | Le ranking hybride utilise toujours les query_terms originaux (pas les expanded) | Cohérent avec l'objectif actuel (rappel, pas scoring) |
| Dictionnaires en français comme pivot | Les concepts sont nommés en FR, les autres langues sont des mappings | Acceptable pour un projet suisse francophone |

---

## 7. Tests

### 7.1 Tests unitaires

`tests/unit/domain/test_query_expansion.py` — 28 tests :

| Classe | Nombre | Couverture |
|---|---|---|
| `TestExpandQueryFrench` | 4 | Synonymes FR, normalisation accents |
| `TestExpandQueryGerman` | 5 | DE→FR (verkehr, gesundheit, wetter, umwelt), umlauts |
| `TestExpandQueryItalian` | 4 | IT→FR (trasporto, salute, meteo), accents |
| `TestExpandQueryEnglish` | 4 | EN→FR (weather, environment, health), case insensitive |
| `TestExpandQueryEdgeCases` | 7 | Vide, inconnu, tokens courts, ponctuation, déduplication, traçabilité |
| `TestDictionaryConsistency` | 2 | Concepts FR ont une entrée multilingue, pas de termes vides |
| `TestQueryExpanderWithCustomDictionaries` | 2 | Injection de dictionnaires personnalisés |

### 7.2 Tests de non-régression

Les 80 tests unitaires du projet passent, incluant les 26 tests de `test_ranking.py` (inchangés).

---

## 8. Évolution future

1. **M7** : Enrichissement du dictionnaire basé sur les analytics de recherche (termes sans résultat)
2. **M7** : Ajout d'un stemmer léger pour le français et l'allemand
3. **M7** : Pondération des termes étendus dans le scoring hybride
4. **M7** : Intégration potentielle d'un thésaurus externe (EuroVoc, GEMET)