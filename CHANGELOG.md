# Changelog - PDS-Portail

Toutes les modifications notables de ce projet seront documentées dans ce fichier.
Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/) et ce projet respecte le [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] (En cours - Milestones M6 & M7)
### Added (Ajouts)
- PDS-45 : Métriques d'ingestion CKAN — table `sync_metrics`, endpoint `GET /api/v1/internal/sync/metrics`, refactorisation extraction `RunSyncCycleUseCase` (élimination duplication ADR-003) (M7).
- PDS-40 : Recherche différenciante avec ranking hybride explicable et mise en avant de la pertinence (M6).
- PDS-41 : Recherche multilingue FR/DE/IT/EN — dictionnaire 20 concepts × 4 langues, 15 concepts de synonymes métier, expansion de requête traçable intégrée au pipeline de recherche (M6).
- PDS-42 : Affichage du "Pourquoi ce résultat" dans les cartes de recherche et refonte de la page pondération (M6).
- PDS-43 : Comparaison guidée de datasets — sélection de 2 à 4 datasets depuis la recherche, tableau comparatif avec badges de qualité colorés (OKLCH sémantique), vue desktop/mobile responsive, endpoint batch optimisé (1 seul round-trip DB) (M6).
- PDS-47 : Instrumentation KPI de base pour le Time-to-first-relevant-dataset (M7, planifié).
- PDS-50 : Documentation technique — glossaire (27 termes), diagramme de flux Mermaid, modèle de menaces (6 menaces, trust boundaries), section Documentation dans le README.
- PDS-51 : Mise en conformité Svelte 5 best practices — `app.html` lang="fr", suppression meta non standard, `onMount` → `$effect`, titres de page uniques sur les 4 pages.
- PDS-49 : Validation de la persistance du cache Render — ADR-024 accepté, protocole de vérification avant/après redéploiement documenté dans la procédure d'exploitation, mode dégradé explicité (M7).
- PDS-52 : Ingestion CKAN incrémentale avec suivi d'offset persistant — table `sync_state`, reprise après redéploiement, endpoints `POST /api/v1/internal/sync` et `GET /api/v1/internal/sync/status` (M7).
- PDS-44 : Index FTS5 et facettes pré-calculées — table `facets_cache` mise à jour après chaque cycle d'ingestion, fallback sur agrégation directe si cache vide. Réduction de la charge SQL par requête de recherche (M7).
- PDS-53 : Synchro CKAN différentielle — une fois le catalogue complet chargé, seuls les datasets modifiés depuis `last_full_sync` sont récupérés (filtre `fq=metadata_modified`). Réduit les requêtes CKAN de ~100 à ~1-3 par cycle, fraîcheur quasi temps réel (M7).
- Gouvernance d'ouverture de session en mode production : lecture courte obligatoire, ancrage backlog/SPEC/ADR, validation ciblée et traçabilité d'exploitation.
- PDS-46 : Cache multi-niveaux avec invalidation fine — clés versionnées par type d'endpoint (search/dataset_detail/resource_detail/compare), TTL 24h (ADR-007), invalidation ciblée déclenchée après sync CKAN, instrumentation hit/miss/ratio via `GET /api/v1/internal/cache/stats`, feature flag `QUERY_CACHE_ENABLED` (M7).
- PDS-54 : Rate-limiting global sur l'API publique (slowapi, 30 req/min) et timeout CKAN configurable via `CKAN_HTTP_TIMEOUT_SECONDS` (M8).
- PDS-55 : Durcissement du Dockerfile — build multi-stage, utilisateur non-root `appuser`, `HEALTHCHECK`, `uv cache clean` (M8).
- PDS-56 : Content Security Policy (CSP) stricte — header `Content-Security-Policy` injecté via `hooks.server.ts`, script-src self (blocage inline), connect-src restreint à `self` + `pds-portail-backend.fly.dev` + `opendata.swiss`, renommage `svelte.config.js` → `svelte.config.ts` (M8).
- PDS-57 : Typage des interfaces SvelteKit (`App.PageData`, `App.Error`, `App.Locals`, `App.Platform`) dans `app.d.ts` et validation runtime du contrat `CompareResponse` dans `comparer/+page.ts` via `isCompareResponse` (contrat `$lib/contracts/compare`), suppression du cast brutal `as CompareResponse` (M8).

### Fixed
- PDS-40 : suppression des warnings SQLAlchemy de produit cartésien dans les requêtes de recherche/facettes afin de fiabiliser les comptages et la recherche en exploitation.
- PDS-40 : correction du calcul de fraicheur — `metadata_modified` CKAN (mis à jour par le harvester) remplacé par `max(resources[].last_modified)` pour refléter l'âge réel des fichiers de données.

## [1.0.0] - 2026-06-23 (Stabilisation MVP)
### Added
- MVP déployé en production (Vercel + Render).
- Interface de recherche SvelteKit 5 (UI Neo-Brutaliste OKLCH).
- Calcul dynamique du score de qualité et de la fraîcheur.
- Ingestion automatisée et normalisation de l'API CKAN opendata.swiss.

### Fixed
- PDS-15 : Correction du CORS proxy et du passage des headers de compression `ERR_CONTENT_DECODING_FAILED`.
- PDS-18 : Tolérance au parsing des champs CKAN éditoriaux multilingues (support objet ou string).
- PDS-29 : Lancement du bootstrap CKAN limité avec gestion des redirections HTTP 302.

### Security
- PDS-54 : Protection anti-abus de l'API publique avec rate-limiting slowapi (30 req/min) et timeout strict sur les appels CKAN externes (30s par défaut, configurable).

