# ADR-035 : Contrat OpenAPI comme source de vérité unique backend↔frontend et génération automatique des types TypeScript

## Statut

Accepted

## Date

2026-07-08

## Contexte

Le backend FastAPI expose automatiquement un schéma OpenAPI décrivant l'ensemble des endpoints, paramètres, DTO et codes d'erreur de l'API. Aujourd'hui, les types TypeScript utilisés par le frontend SvelteKit sont écrits et maintenus manuellement dans `frontend/src/lib/types/`.

Cette duplication manuelle présente trois risques :
1. **Désynchronisation silencieuse** : un champ ajouté ou renommé côté backend n'est pas détecté côté frontend avant l'exécution (bug runtime).
2. **God DTOs** : pour éviter de recréer des types, on est tenté de réutiliser des objets fourre-tout, dégradant la précision du typage.
3. **Charge mentale inutile** : chaque changement de schéma Pydantic nécessite une mise à jour manuelle des types TypeScript.

L'audit d'un architecte externe (juillet 2026) a confirmé ce diagnostic : maintenir la synchronisation manuellement est une source de bugs majeure en solo dev.

## Decision Drivers

- **Fiabilité** : éliminer le risque de divergence backend↔frontend
- **Sécurité** : exploiter le typage strict TypeScript pour détecter les erreurs d'API à la compilation plutôt qu'à l'exécution
- **Vélocité** : un seul changement côté backend (schéma Pydantic) doit se propager automatiquement au frontend
- **Simplicité** : pas d'over-engineering (pas de gRPC, pas de GraphQL, pas de codegen lourd)
- **Progressivité** : ne pas casser la production, permettre une migration par étapes
- **Cohérence** : respecter ADR-007 qui masque `/docs` en production mais garde le schéma interne accessible en dev/CI

## Options considérées

### Option 1 : Continuer à écrire les types manuellement (statu quo)

Avantages :
- Aucun changement requis
- Contrôle total sur les types frontend

Inconvénients :
- Désynchronisation silencieuse possible
- Charge manuelle de maintenance
- Risque de God DTOs
- Ne répond pas à la recommandation de l'architecte

### Option 2 : `openapi-typescript` — génération de types uniquement (retenue)

L'outil [openapi-typescript](https://openapi-ts.dev/) lit un schéma OpenAPI et génère un fichier `.d.ts` contenant tous les types de requêtes, réponses, paramètres et schémas.

Avantages :
- Léger (~50 Ko, zéro dépendance runtime)
- Génère uniquement des types, pas de code (pas de hooks fetch imposés)
- Intégration simple dans le build (`npx openapi-typescript`)
- Compatible avec le typage existant (les types manuels peuvent cohabiter)
- Open source, maintenu activement

Inconvénients :
- Nécessite un schéma OpenAPI accessible en CI
- Les types générés suivent la nomenclature OpenAPI (`components["schemas"]["DatasetDetail"]`), moins lisibles que des noms courts
- Ne génère pas de fonctions fetch typées

### Option 3 : `orval` — génération de types + hooks fetch typés

[orval](https://orval.dev/) lit un schéma OpenAPI et génère des types + des fonctions fetch React/Vue/Svelte.

Avantages :
- Génération complète (types + hooks fetch typés)
- Plus de code boilerplate à écrire pour les appels API

Inconvénients :
- Plus lourd, impose une convention de fetch
- Les hooks générés sont orientés React/Vue ; le support Svelte est expérimental
- Over-engineering pour un projet solo avec une API simple
- Changement plus invasif dans le codebase frontend

## Décision

Adopter le schéma OpenAPI généré par FastAPI comme **contrat unique et source de vérité** entre le backend et le frontend.

1. **Outil retenu** : `openapi-typescript` (Option 2), pour sa légèreté et sa non-intrusivité.
2. **Mise en œuvre** : en deux temps :
   - **M11/M16 (documentation)** : rédiger ADR-035 + SPEC-016, créer le ticket d'implémentation dans M16
   - **M16 (implémentation)** : installer l'outil, générer en parallèle, migrer progressivement
3. **`orval` (Option 3)** reste une cible possible post-MVP si les hooks fetch typés sont jugés utiles. Cette évolution fera l'objet d'un ADR distinct.
4. **En production** : le fichier généré est utilisé par `svelte-check` mais n'est pas servi au navigateur (types seulement).
5. **CI** : la génération est intégrée dans `make quality-frontend` avant `svelte-check`. Si le schéma OpenAPI change d'une manière incompatible avec le frontend, le build échoue avant déploiement.

## Conséquences

### Positives

- **Plus de divergence BE↔FE** : tout changement de schéma Pydantic est répercuté automatiquement
- **Détection précoce des bugs** : une incompatibilité API est détectée au build, pas en production
- **Vélocité** : un seul fichier à modifier côté backend, le frontend suit automatiquement
- **Documentation vivante** : le schéma OpenAPI devient l'unique référence du contrat API
- **Conformité à la recommandation architecte** : le trou dans la raquette est comblé

### Négatives

- **Étape supplémentaire dans le build** : la génération ajoute ~2 secondes au `make quality-frontend`
- **Nomenclature OpenAPI** : les noms de types générés sont plus verbeux (`components["schemas"]["DatasetDetail"]`)
- **Migration progressive nécessaire** : ne pas casser les types manuels existants pendant la transition
- **Dépendance au schéma OpenAPI** : si FastAPI change son format de schéma, l'outil doit suivre

### Actions requises

1. Produire SPEC-016 détaillant le plan de mise en œuvre étape par étape
2. Installer `openapi-typescript` en devDependency dans `frontend/` (M16)
3. Créer le script `generate:api-types` dans `frontend/package.json` (M16)
4. Intégrer la génération dans `make quality-frontend` avant `svelte-check` (M16)
5. Migrer progressivement les types manuels vers les alias générés (M16)
6. Documenter le processus dans le README frontend

## Liens

- ADR lié : [0007-cache-ttl-and-api-docs.md](0007-cache-ttl-and-api-docs.md) (masquage `/docs` en production, schéma interne dispo en dev/CI)
- ADR lié : [0003-internal-architecture.md](0003-internal-architecture.md) (Clean Architecture, stabilité des ports et DTO)
- ADR lié : [0034-integration-polar-checkout-session-et-politique-webhooks.md](0034-integration-polar-checkout-session-et-politique-webhooks.md)
- SPEC liée : [spec-016-generation-types-openapi.md](../../20-technique/01-spec/spec-016-generation-types-openapi.md)
- SPEC liée : [spec-001-technical-architecture.md](../../20-technique/01-spec/spec-001-technical-architecture.md)
- SPEC liée : [spec-006-composants-api-svelte.md](../../20-technique/01-spec/spec-006-composants-api-svelte.md)
- Roadmap : [roadmap-mvp.md](../../10-produit/03-roadmap/roadmap-mvp.md)
- Backlog : M16 — Optimisation