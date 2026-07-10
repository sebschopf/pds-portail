# Changelog - PDS-Portail

Toutes les modifications notables de ce projet seront documentées dans ce fichier.
Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/) et ce projet respecte le [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- PDS-106: Tests backend — couverture des chemins critiques `invalidate_cache_after_sync`, `compare_adapter`, `cache_repository` (conflits/upsert), `_search_helpers.parse_tags`. 9 tests, 366 lignes, couverture backend → 91.41%.
- PDS-M11: Suppression de `uv` du stage de production Dockerfile — .venv copié depuis le build, CMD/HEALTHCHECK utilisent python directement (recommandation architecte).
- PDS-M11: Activation mypy strict (`disallow_untyped_defs = true`) — 1 seule fonction non-annotée corrigée dans tout le codebase.
- PDS-125: ADR-035 — Contrat OpenAPI comme source de vérité unique backend↔frontend, génération automatique des types TypeScript.
- PDS-125: SPEC-016 — Pipeline de génération des types TypeScript en 4 phases, implémenté (openapi-typescript, make quality, contrats stricts).
- PDS-125: Durcissement du contrat backend — `RankingSignals` en modèle Pydantic, suppression des `default_factory=list` sur les DTOs cœur UI (SearchDatasetItem, CompareItem, DatasetDetailResponse) pour un typage TypeScript strict.
- PDS-125: Migration des types frontend — alias explicites `components['schemas']['...']` dans search.ts, compare.ts, ranking.ts, watchers.ts.
- PDS-125: Audit terminé — correctif `ranking_signals: null` dans `CardDataset.test.ts` (svelte-check 0 erreur), ADR-035 → Accepted.
- PDS-122: `polar_customer_id` dans le port, migration SQLite, limite 10 datasets affichée dans le manuel, WatchDataset et /alertes.
- PDS-121.2: proxys SvelteKit pour watchers en production Vercel (magic-link, watchers CRUD, alerts).
- PDS-121.3: champ `polar_customer_id` dans WatcherModel, extraction webhook `order.created`, limite `MAX_WATCHED_DATASETS=10`.
- Documentation utilisateur : section "Service payant" dans le manuel, page /alertes avec "Rappel du fonctionnement" et récupération email perdu.
- PDS-121: mise en conformité Polar Checkout et Webhooks — Checkout link hébergé, webhook canonique, tolérance cancelled/canceled.
- PDS-86: tables `watchers`, `watched_datasets`, `change_log` et repositories.
- PDS-87: `DetectChangesUseCase` dans le cycle de sync, 5 types de changements détectés.
- PDS-89: endpoints Polar/watchers/alerts (webhook, CRUD, historique).
- PDS-90: UI surveillance frontend (modale abonnement, badge suivi, page alertes).
- PDS-111: module support interne protégé — diagnostics par email, renvoi magic link audité, page SSR.
- PDS-114: ADR-034 acte checkout frontend hébergé et mapping webhook minimal.
- PDS-91: ADR-029 réalignée sur envoi email smtplib + SMTP Brevo.
- PDS-117.1: flux magic link bout en bout — endpoints consume/create, validation hash/expiration, intégration frontend /alertes?magic=, templates email.

### Changed
- PDS-88: rate-limit strict par couple watcher+dataset sur 24h pour alertes email.
- PDS-88: `watched_datasets.last_alert_sent_at` pour traçabilité du throttling.
- PDS-115: page /alertes alignée contrat V1, persistance token localStorage.
- PDS-116: webhook `order.created` valide dataset avant mutation, réutilise watcher existant, resynchronise `polar_subscription_id`.
- PDS-118: refactor tests magic link pour clocks contrôlables et horodatages déterministes.
- Roadmap M11 mise à jour.
- PDS-111/PDS-112: séparation `.env.local` / `.env.test`, `INTERNAL_API_TOKEN` dans le template.

### Fixed
- PDS-121: correction checkout Polar mode Checkout Link (`PUBLIC_POLAR_CHECKOUT_URL`).
- PDS-119: message d'erreur unifié anti-énumération pour magic link.
- PDS-88/PDS-89: alignement typage strict Pylance/mypy, stabilité fakes de tests.
- PDS-116: webhook dataset inconnu n'écrit plus d'état partiel, réactivation watcher suspendu.
- PDS-115: token watcher persisté automatiquement après accès serveur réussi.
- PDS-111/PDS-112: durcissement support interne — Basic Auth serveur, dispatch_status queued, tests erreurs, runbook R002 §4.7.

## [1.1.5] - 2026-07-03

### Added
- PDS-82: clôture exploration ressources — parsing tabulaire + RDF V1, analyse heuristique, endpoint unique `/api/v1/resources/{id}/explore`.
- PDS-84: composant ExploreDataset Svelte avec états (locked→loading→error→success), localStorage clé API, tableau WCAG AA, 35 tests.
- PDS-109: hardening exploration prod — cache, quota asymétrique (miss=consomme, hit=non), timeout réseau, invalidation ciblée.
- PDS-108: baseline QA tests backend — rapport, modules critiques, cibles couverture progressives, gates 2 phases.
- PDS-80: ADR-027 — clé API UUID v4 hashée SHA-256, table `licenses`, header `X-API-Key`.
- PDS-81: implémentation infrastructure licences — LicenseModel, repository, dépendance `require_license`.

## [1.1.4] - 2026-07-01

### Added
- PDS-102: multi-sélection tags recherche, URL partageable, compatibilité ascendante `tag=`.
- M11: milestone Monétisation & Exploration Premium.
- SPEC-008: exploration payante — endpoint, parsing CSV/JSON, analyse sémantique, licenses avec quotas.
- SPEC-009: surveillance changements — abonnement 5 CHF/mois, 10 datasets max, alertes email magic links.
- SPEC-010: exploration I14Y — faisabilité multisource.
- PRD-F12 à F17: exigences M11 ajoutées au PRD, matrice de traçabilité mise à jour.
- Index specs mis à jour avec SPEC-008/009/010.
- PDS-78~79 remplacés par PDS-80 à PDS-90 (décomposition granulaire).
- PDS-80 à PDS-92: ADR et tickets infrastructure M11 (clé API, exploration, paiement Polar, emails, magic links, tables, détection, alertes, endpoints, frontend).
- Fiche portfolio ajoutée.

### Fixed
- PDS-84/PDS-108: prévisualisation ressource avec état sémantique explicite, badges accessibilité.
- Frontend recherche: navigation facette tags multi-sélection améliorée (focus, clic, scroll).
- PDS-104: refactor search_adapter en orchestrateur SRP, correction doublon SQLAlchemy.
- PDS-103: maillage documentaire synchronisé — SPEC-007 réalignée, rapport révision, index mis à jour.
- PDS-101: validation production recherche combinée, sentinelles d'intégration, rapport p50/p95.
- PDS-100: hardening production recherche — CACHE_SCHEMA_VERSION=2, FTS5 défensif, runbook rollback.
- PDS-94/PDS-99: correctif CORS+502, DROP TABLE → IF NOT EXISTS, exception handler global.
- PDS-99: parsing CKAN tags multilingues, normalisation ingestion, déduplication facettes.
- PDS-96: migration FTS5 index tags, reconstruction conditionnelle, backfill complet.
- PDS-96: preuve rollback/migration miroir — test schéma ancien → reconstruction auto.
- PDS-97: expansion multilingue branchée dans SearchDatasetsUseCase, propagation FTS5.
- PDS-98: facettes alignées scope recherche, correction filtre tag exact.

## [1.1.3] — M10 Préparation multisource

### Added
- PDS-71: colonne `source` sur tables cache, migration auto, préparation multisource ADR-026.
- PDS-72: protocole veille I14Y/metadata.swiss — 8 signaux bascule, première vérification 2026-06-28.
- PDS-74: roadmap post-MVP v2.0 — refonte complète avec contexte, rétrospective M1-M9, planning 2026-2028.
- PDS-76: page `/suite` — transition opendata.swiss → metadata.swiss, composants Timeline et ExternalLinkIcon.

## [1.1.2] - 2026-06-27

### Added
- PDS-69: polish cosmétique — icônes SVG néo-brutalistes, espacements aérés, pied de page auteur.
- Favicon cube de données SVG OKLCH 32×32.
- Footer enrichi — identité, source opendata.swiss, manuel, crédits, mentions WCAG 2.2 AA et RGPD.
- Page `/manuel` — 6 sections (rechercher, comprendre, personnaliser, comparer, ressources, accessibilité).

### Fixed
- PDS-70: timeout recherche 3+ termes — limite `MAX_EXPANSION_TERMS=12`.
- PDS-70: index FTS5 migré `unicode61 remove_diacritics 2`, triggers auto, backfill.
- PDS-70: recherche instantanée debounce 400ms sans bouton.
- PDS-71: accents français manquants dans ~185 chaînes UI.

## [1.1.1] - 2026-06-27

### Fixed
- each_key_duplicate: dédoublonnage facettes dans `optionList()` (Set) et clés indexées.

## [1.1.0] - 2026-06-27 (Milestones M6, M7, M8, M9)

### Fixed (Corrections)
- PDS-69: audit recherche combinée — mock API ignorait tag, org comparait sur mauvais champ, debounce indépendant par facette, 16 tests.

### Added (Ajouts)
- PDS-64: nettoyage UI — bits-ui retiré (~50KB), PageLayout factorisé, debounce 300ms facettes.
- PDS-63: transitions Svelte natives — fly/fade pages, slide CompareBar, crossfade résultats, prefers-reduced-motion.
- PDS-62: page 404 personnalisée — carte SVG 26 cantons suisses néo-brutaliste, liens recherche par canton.
- PDS-61: états vides illustrés — composant EmptyState réutilisable, variantes empty/error, 8 remplacements.
- PDS-60: skeletons — composant Skeleton shimmer OKLCH, SkeletonCard anti-CLS.
- PDS-67: librairie icônes SVG néo-brutalistes — 6 icônes, stroke-width 2.5, currentColor.
- PDS-66: tokens motion — durées/easings, prefers-reduced-motion → 0ms.
- PDS-38: durcissement HTTPS/headers sécurité — SecurityHeadersMiddleware, hooks.server.ts, script vérification.
- PDS-65: design system Atomic Design — tokens CSS, atoms/molecules/organisms, barrel exports.
- PDS-45: métriques ingestion CKAN — table sync_metrics, endpoint métriques.
- PDS-40: ranking hybride explicable, mise en avant pertinence.
- PDS-41: recherche multilingue FR/DE/IT/EN — 20 concepts × 4 langues, expansion traçable.
- PDS-42: "Pourquoi ce résultat" dans cartes recherche, refonte pondération.
- PDS-43: comparaison guidée datasets — sélection 2-4, tableau comparatif, endpoint batch.
- PDS-47: instrumentation KPI Time-to-first-relevant-dataset (planifié).
- PDS-50: documentation technique — glossaire 27 termes, diagramme Mermaid, modèle menaces.
- PDS-51: conformité Svelte 5 — lang="fr", $effect, titres de page uniques.
- PDS-49: validation persistance cache Render — ADR-024, protocole vérification.
- PDS-52: ingestion CKAN incrémentale — table sync_state, reprise après redéploiement.
- PDS-44: index FTS5, facettes pré-calculées — table facets_cache.
- PDS-53: synchro CKAN différentielle — filtre metadata_modified.
- Gouvernance d'ouverture de session production.
- PDS-46: cache multi-niveaux — invalidation fine, TTL 24h, instrumentation hit/miss.
- PDS-54: rate-limiting slowapi 30 req/min, timeout CKAN configurable.
- PDS-55: Dockerfile multi-stage, non-root, HEALTHCHECK.
- PDS-56: CSP stricte — hooks.server.ts, script-src self.
- PDS-57: typage SvelteKit — App.PageData, validation runtime CompareResponse.
- PDS-37: baseline SEO technique — métadonnées, sitemap.xml, robots.txt.
- PDS-59: métriques qualité Lighthouse intégrées dans make quality.
- PDS-58: métriques usage via cache — top-queries, zero-results.
- PDS-68: documentation Design System — SPEC-006, guide icônes, checklist accessibilité 42 items.

### Fixed
- PDS-40: suppression warnings SQLAlchemy produit cartésien recherche/facettes.
- PDS-40: correction calcul fraîcheur — `max(resources[].last_modified)` au lieu de `metadata_modified` CKAN.

## [1.0.0] - 2026-06-23 (Stabilisation MVP)

### Added
- MVP déployé en production (Vercel + Render).
- Interface de recherche SvelteKit 5, UI Neo-Brutaliste OKLCH.
- Score qualité et fraîcheur dynamiques.
- Ingestion automatisée CKAN opendata.swiss.

### Fixed
- PDS-15: CORS proxy et headers compression `ERR_CONTENT_DECODING_FAILED`.
- PDS-18: tolérance parsing champs CKAN multilingues (objet ou string).
- PDS-29: bootstrap CKAN limité, gestion redirections HTTP 302.

### Security
- PDS-54: rate-limiting slowapi 30 req/min, timeout CKAN.