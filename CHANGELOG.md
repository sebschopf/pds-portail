# Changelog - PDS-Portail

Toutes les modifications notables de ce projet seront documentées dans ce fichier.
Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/) et ce projet respecte le [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2026-06-27
### Fixed
- each_key_duplicate : dédoublonnage des facettes dans `optionList()` (Set) et clés indexées dans `+page.svelte` (`facet.name-idx`)

## [1.1.0] - 2026-06-27 (Milestones M6, M7, M8, M9)
### Fixed (Corrections)
- PDS-69 : Audit recherche combinée tag/format/org — le mock API ignorait le filtre `tag` (paramètre parsé mais jamais appliqué), le filtre `org` comparait sur `dataset.id` au lieu de `dataset.org_id`, et le debounce partagé entre facettes pouvait perdre une sélection lors de changements rapides. Les 3 filtres sont désormais cumulables et indépendants, chacun avec son propre timer 300ms. 16 nouveaux tests unitaires ajoutés (`search-api.test.ts`). (M9)

### Added (Ajouts)
- PDS-64 : Nettoyage et fondations UI — bits-ui retiré (~50KB économisés, 0 import), PageLayout factorise `.stack` (4 pages), debounce 300ms sur facets+sort dans FiltersPanel. (M9)
- PDS-63 : Transitions et micro-interactions — fade+fly entre les pages via `{#key page.url.pathname}` dans `+layout.svelte` (in:fly 8px/300ms, out:fade 150ms), slide fluide du `CompareBar` (300ms), crossfade des résultats de recherche via `{#key resultsKey}` (in:fade 300ms, out:fade 150ms). Toutes les durées respectent les tokens `--duration-fast` (150ms) / `--duration-normal` (300ms) / `--duration-slow` (500ms). `prefers-reduced-motion` forcé à 0ms via `motion.css`. Zéro librairie externe, transitions Svelte natives uniquement. (M9)
- PDS-62 : Page 404 personnalisée — carte interactive des 26 cantons suisses en SVG néo-brutaliste (`SwissCantonsMap.svelte`), chaque canton est un lien vers une recherche opendata.swiss pré-remplie avec l'organisation cantonale. Remplace la page d'erreur par défaut de SvelteKit. Design OKLCH, messages français conformes au guide rédactionnel §3.2, accessibilité (`role="alert"`, `aria-live="assertive"`, navigation clavier SVG avec `focus-visible`, labels ARIA par canton). (M9)
- PDS-61 : États vides illustrés — composant `EmptyState` réutilisable (icône + titre + description + action optionnelle), variantes `empty`/`error`, remplacement des 8 messages texte passe-partout dans `+page.svelte` (recherche), `comparer/+page.svelte` et `dataset/[id]/+page.svelte` par des états illustrés conformes au guide rédactionnel, suppression des CSS orphelines `.state`, `.state-danger`, `.error-banner`. (M9)
- PDS-60 : Skeletons et états de chargement — composant `Skeleton` réutilisable avec shimmer OKLCH et support `prefers-reduced-motion`, molécule `SkeletonCard` alignée sur `CardDataset` pour éviter le CLS, remplacement de tous les textes "Chargement..." dans `+layout.svelte` (barre de navigation) et `+page.svelte` (3 squelettes pendant la recherche). (M9)
- PDS-67 : Librairie d'icônes SVG néo-brutalistes — 6 icônes : SearchIcon, FilterIcon, DatasetIcon, CompareIcon, EmptyIcon, ErrorIcon. Style `stroke-width: 2.5`, `stroke-linecap: square`, `currentColor`. Props `size`/`class`. Accessibles (`aria-label`). Exportées via `$lib/index.ts`. Pas de CDN (ADR-014). (M9)
- PDS-66 : Tokens de motion et contrat d'animation — `tokens/motion.css` avec `--duration-instant` (0ms), `--duration-fast` (150ms), `--duration-normal` (300ms), `--duration-slow` (500ms) et easings `--easing-standard`, `--easing-emphasized`, `--easing-decelerated`. `prefers-reduced-motion: reduce` force toutes les durées à 0ms. Importé dans `tokens/index.css`, documenté dans SPEC-003 §3.6. (M9)
- PDS-38 : Durcissement HTTPS et headers de sécurité web — middleware `SecurityHeadersMiddleware` backend (HSTS, X-Content-Type-Options, X-Frame-Options, COOP, Referrer-Policy, Permissions-Policy), headers injectés dans `hooks.server.ts` frontend, script `scripts/check-security-headers.sh` de vérification HTTP, Trusted Types en mode rapport via CSP, documentation des compromis MVP (M8).
- PDS-65 : Réorganisation du design system en Atomic Design — tokens CSS extraits (colors, typography, spacing), composants rangés en atoms/molecules/organisms, barrel `$lib/index.ts` ré-export, document `spec-004-ui-design-system.md`, script `validate-design-system.mjs` adapté pour suivre les `@import` CSS (M9).
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
- PDS-37 : Baseline SEO technique MVP — métadonnées par type de page (title, meta description, canonical, robots, sitemap), document `Doc/20-technique/05-seo/seo-baseline.md`, `sitemap.xml` statique, `robots.txt` avec directive Sitemap, cartographie des écarts Lighthouse SEO et limites MVP explicites. Références multi-moteurs (Google, Bing, IBM). (M8).
- PDS-59 : Baseline de métriques qualité sans blocage automatique — intégration Lighthouse dans `make quality` (desktop ≥90, mobile ≥70), script `check-lighthouse-thresholds.mjs`, document `Doc/20-technique/02-exploitation/slo-baseline.md` listant les métriques et leur vérification, pas de CI/CD externe ni dashboard (M8).
- PDS-58 : Métriques d'usage minimales via le cache existant — endpoints internes `GET /api/v1/internal/metrics/top-queries` (top N par hit_count) et `GET /api/v1/internal/metrics/zero-results` (requêtes sans résultat), exploite la table `query_cache` (PDS-46) sans infrastructure supplémentaire, protégés par `INTERNAL_API_TOKEN`, pas de PII (M8).
- PDS-68 : Documentation du Design System — trois nouveaux documents techniques : SPEC-006 (Référence des Composants / UI Catalog avec Props, Events, Slots et exemples pour les 11 composants), Guide de gestion des Icônes et Assets SVG (pipeline SVGO → Svelte, règles currentColor/viewBox, checklist conformité) et Checklist d'Accessibilité QA manuelle (42 items sur 5 parcours critiques : clavier, lecteur d'écran, zoom 200%, motion réduite, mode sombre). README table des matières dans `Doc/20-technique/01-spec/` et mise à jour de l'index `Doc/README.md` (M9).

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