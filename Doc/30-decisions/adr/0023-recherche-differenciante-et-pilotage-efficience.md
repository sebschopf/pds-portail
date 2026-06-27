# ADR-023 : Recherche differenciante et pilotage de l'efficience

## Statut

Proposed

## Date

2026-06-20

## Contexte

Le MVP couvre la navigation et la qualite de base sur opendata.swiss.
Pour aller au-dela des catalogues officiels generalistes, PDS-Portail doit differencier sa valeur sur:

- pertinence recherche orientee usage,
- explicabilite des resultats,
- efficience technique mesurable,
- boucle d'amelioration pilotee par KPI.

Sans cadre explicite, les optimisations risquent de rester ponctuelles et difficiles a auditer.

References produit associees:
- PRD-F09, PRD-F10, PRD-F11
- PRD-NFR02, PRD-NFR09

## Decision Drivers

- Utilite immediate pour public non-technique
- Performance stable sur infra contrainte
- Tracabilite forte des arbitrages
- Cohabitation avec politique privacy by design

## Options considerees

### Option 1 : Evolutions opportunistes non cadrees

Avantages :
- Faible cout initial

Inconvenients :
- Effets disperses, difficilement mesurables
- Priorisation instable

### Option 2 : Programme post-MVP structure en deux milestones (retenue)

Avantages :
- Trajectoire lisible et auditable
- Priorisation impact/effort plus robuste
- Mesure continue de la valeur produit

Inconvenients :
- Besoin de discipline sur instrumentation et runbooks

## Decision

Adopter une trajectoire post-MVP en deux volets:

1. **M6 - Recherche differenciante et lisibilite de la pertinence**
   - Ranking hybride explicable
   - Recherche multilingue + synonymes metier
   - Exposition de "Pourquoi ce resultat ?"
   - Comparaison guidee de datasets

2. **M7 - Performance, fiabilite et pilotage par KPI**
   - Ranking hybride explicable
   - Recherche multilingue + synonymes metier
   - Index recherche et facettes pre-calculees
   - **PDS-70** : Index FTS5 avec `remove_diacritics=2` + limite anti-explosion des termes d'expansion (`MAX_EXPANSION_TERMS=12`) + triggers auto + backfill
   - Ingestion CKAN incremental prioritaire
   - Cache multi-niveaux avec invalidation fine
   - KPI d'usage/pertinence + SLO de release

Cadre KPI minimal obligatoire:

- TTFRD (Time-to-first-relevant-dataset)
- Taux de reformulation de requete
- Taux de clic utile (resultat -> detail -> ressource)
- Latence API p95 (search, dataset detail)

## Consequences

### Positives

- Meilleure valeur differenciante face aux catalogues exhaustifs
- Arbitrages techniques et produit fondes sur mesures
- Meilleure predictibilite des releases

### Negatives

- Cout initial d'instrumentation et de maintenance
- Besoin de revue reguliere des KPI

### Actions requises

- Mettre en oeuvre les taches PDS-40 a PDS-49.
- Etendre les gates de qualite vers des checks performance/SLO.
- Documenter les protocoles de mesure et les limites.

## Liens

- ADR lie : [0002-test-policy.md](0002-test-policy.md)
- ADR lie : [0003-internal-architecture.md](0003-internal-architecture.md)
- ADR lie : [0005-frontend-accessibility-privacy.md](0005-frontend-accessibility-privacy.md)
- ADR lie : [0007-cache-ttl-and-api-docs.md](0007-cache-ttl-and-api-docs.md)
- ADR lie : [0008-cicd-environments.md](0008-cicd-environments.md)
- ADR lie : [0021-web-transport-and-security-headers-policy.md](0021-web-transport-and-security-headers-policy.md)
- PRD : [prd.md](../../10-produit/02-prd/prd.md)
- SPEC : [spec-001-technical-architecture.md](../../20-technique/01-spec/spec-001-technical-architecture.md)
- Backlog : [doc-004 - cadrage-post-mvp-differenciation-catalogues-officiels.md](../../../backlog/docs/doc-004%20-%20cadrage-post-mvp-differenciation-catalogues-officiels.md)