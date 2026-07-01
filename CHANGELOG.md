# Changelog - PDS-Portail

Toutes les modifications notables de ce projet seront documentées dans ce fichier.
Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/) et ce projet respecte le [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — M11 Monétisation & Exploration Premium

## [1.1.4] - 2026-07-01
### Added
- PDS-102 : Frontend recherche migré vers la multi-sélection de tags (`selectedTags`) avec URL partageable/réhydratable (`tags=` pour multi, `tag=` conservé en legacy mono-tag), compatibilité ascendante des anciens liens `tag=...`, adaptation du mock API au filtrage multi-tags (OR), et extension des tests frontend (FiltersPanel, search-context, search-api) pour couvrir le nouveau comportement.
- M11 : Milestone Monétisation & Exploration Premium créé (m-14).
- SPEC-008 : Service payant Exploration des champs — endpoint `POST /api/v1/resources/{id}/explore` protégé par clé API, parsing CSV/JSON avec colonnes/types/remplissage/échantillons/stats, analyse sémantique automatique (géo/temporel/statistique/catégoriel/croisement), table `licenses` avec quotas et rate limiting, composant `ExploreDataset.svelte` avec localStorage et WCAG AA. Traçabilité PRD-F12, PRD-F13, PRD-F17. Document : `Doc/20-technique/01-spec/spec-008-service-payant-exploration-champs.md`.
- SPEC-009 : Service payant Surveillance des changements — abonnement 5 CHF/mois (10 datasets max), détection automatique à chaque cycle d'ingestion, alertes email avec magic links (15 min, multi-usage), tables `watchers`/`watched_datasets`/`change_log`/`magic_links`, page `/alertes` tokenisée, paiement Polar MoR CHF natif. Traçabilité PRD-F14, PRD-F15, PRD-F16. Document : `Doc/20-technique/01-spec/spec-009-service-payant-surveillance-changements.md`.
- SPEC-010 : Exploration I14Y — Faisabilité multisource (renuméroté de SPEC-008 pour éviter collision). Document : `Doc/20-technique/01-spec/spec-010-exploration-i14y.md`.
- PRD-F12 à PRD-F17 : Exigences fonctionnelles M11 ajoutées au PRD (exploration, clé API, surveillance, paiement, page /alertes, analyse sémantique). Matrice de traçabilité mise à jour.
- Index specs : `Doc/20-technique/01-spec/README.md` mis à jour avec SPEC-008, SPEC-009, SPEC-010.
- PDS-78~79 : Remplacés par les tickets PDS-80 à PDS-90 (décomposition granulaire avec ADR, specs et dépendances).
- PDS-80 (ADR-027) : Clé API pour l'exploration — token opaque UUID v4 hashé SHA-256, table `licenses`, middleware FastAPI `X-API-Key`, rate limiting par clé, distinct du token watcher (ADR-030). Document : `Doc/30-decisions/adr/0027-cle-api-exploration.md`.
- PDS-81 : Backend Licence API — modèle `LicenseModel`, port `LicenseRepositoryPort`, dépendance `require_license`, protection endpoint exploration.
- PDS-82 : Backend Exploration — endpoint `POST /api/v1/resources/{id}/explore`, parsing CSV/JSON stdlib, dataclasses `ExploredResource`/`ColumnInfo`/`ColumnStats`, cache 24h.
- PDS-83 : Backend Analyse sémantique — module `dataset_analysis.py`, détection géo/temporel/numérique/catégoriel/ID, suggestions et mises en garde en langage naturel.
- PDS-84 : Frontend ExploreDataset — composant Svelte avec clé API, localStorage, tableau des colonnes, section Analyse, WCAG AA.
- PDS-85 (ADR-028) : Paiement Polar pour la surveillance — Polar MoR open-source, CHF natif (130+ devises), webhooks `order.created` et `subscription.cancelled`, SvelteKit adapter, frais transparents (5% + 0.50$). Document : `Doc/30-decisions/adr/0028-paiement-stripe-surveillance.md`.
- PDS-91 (ADR-029) : Envoi d'emails pour la surveillance — smtplib stdlib, templates HTML+texte, déduplication 24h, lien désabonnement, pas de tracking. Document : `Doc/30-decisions/adr/0029-envoi-emails-surveillance.md`.
- PDS-92 (ADR-030) : Magic Links pour /alertes — token temporaire 15min à usage unique dans les emails, token permanent `watchers.token` pour localStorage uniquement (jamais exposé dans les URLs). Double mécanisme : magic link (email) + token permanent (localStorage). Table `magic_links`. Document : `Doc/30-decisions/adr/0030-token-watcher-surveillance.md`.
- PDS-86 : Backend Tables surveillance — `WatcherModel`, `WatchedDatasetModel`, `ChangeLogModel`, migrations, repositories.
- PDS-87 : Backend Détection changements — `DetectChangesUseCase` intégré à `RunSyncCycleUseCase`, 5 types de changements (metadata, ressources, qualité, liens).
- PDS-88 : Backend Alertes email — `SendAlertsUseCase`, smtplib, templates HTML+texte, déduplication 24h, lien désabonnement.
- PDS-89 : Backend Endpoints Polar/watchers/alertes — webhook `order.created`, endpoints CRUD watchers, historique alertes.
- PDS-90 : Frontend WatchDataset + /alertes — modale abonnement Polar (5 CHF/mois), badge Surveillé, page tokenisée avec historique des changements, WCAG AA.
- Fiche portfolio : `Doc/10-produit/description-portfolio.md` décrivant le projet (Problématique/Solution/Défis/Résultats/Modèle économique) pour intégration sur schopfer.moustik.site.

### Fixed
- Frontend recherche : correction de la navigation dans la facette `Categorie / tag` (multi-selection). Le focus n'est plus vole vers le resume des resultats pendant la selection des tags, la selection au clic est plus fluide (ajout/retrait direct), et le composant conserve une navigation lisible sur longues listes (scroll vertical du select multiple).
- PDS-104 : Refactor `search_adapter` finalisé en orchestrateur mince avec extraction SRP des responsabilités vers `search_fts`, `search_facets` et `search_tag_filter`, sans rupture du contrat `/api/v1/search`. Correctif de cohérence de reload des modules d'intégration (`search_facets` et `search_tag_filter`) pour éliminer le doublon implicite `datasets` dans SQLAlchemy (erreur `ambiguous column name: datasets.id`). Validation complète backend: `pytest -q` vert (165 tests) avec couverture maintenue au-dessus du seuil.
- PDS-103 : Maillage documentaire final synchronisé entre runtime et documentation — SPEC-007 réalignée avec l’implémentation effective (expansion backend branchée, stratégie FTS5, dégradation contrôlée), rapport de révision complété avec état de clôture M15 et preuves livrées, index documentaire mis à jour (SPEC/ADR/exploitation), et traçabilité PRD/SPEC/ADR explicitée dans les documents d’exploitation.
- PDS-101 : Validation production recherche combinée réalisée avec deux sentinelles d'intégration supplémentaires (combinaison q+org+fmt+tag+sort, et hit_ratio cache sur scénario combiné), rapport p50/p95 avant/après archivé en exploitation (R003), et décision Go/No-Go explicite publiée (GO conditionnel avec surveillance p95/hit_ratio/stale_entries).
- PDS-100 : Hardening production de la recherche — bump du versionnement de clés (`CACHE_SCHEMA_VERSION=2`) pour invalider proprement le cache search lors d'un changement de contrat, gestion défensive des erreurs FTS5 (`datasets_fts` indisponible, `MATCH` malformé, `bm25` indisponible) avec dégradation contrôlée sans 500 non géré, et mise à jour du runbook d'exploitation avec procédure de rollback explicite (application + cache + reconstruction index FTS5 + requêtes sentinelles).
- PDS-94/PDS-99 : Investigation et confirmation du correctif CORS+502 — le DROP TABLE FTS5 a été remplacé par une vérification `IF NOT EXISTS` dans `create_schema()`, un exception handler global a été ajouté dans `main.py` pour garantir les headers CORS même sur les erreurs 500. Les logs Fly confirment que `/search` répond 200 OK depuis le déploiement.
- PDS-99 : Parsing CKAN des tags multilingues aligné sur les autres champs textuels (`name`/`display_name` acceptent désormais les objets de locales), avec normalisation d'ingestion (trim, lowercase, suppression des accents, compactage espaces) et déduplication des tags pour réduire les doublons sémantiques en facettes.
- PDS-96 : Migration contrôlée de `datasets_fts` pour indexer aussi `tags` (en plus de `id,title,description`) avec reconstruction conditionnelle du schéma historique, mise à jour des triggers INSERT/UPDATE/DELETE et backfill complet. Ajout d'un test d'intégration garantissant qu'un terme présent uniquement dans les tags est trouvable via `q=`.
- PDS-96 : Preuve de rollback/migration miroir ajoutée — test d'intégration qui simule un ancien schéma FTS5 sans `tags`, relance `create_schema()`, vérifie la reconstruction automatique avec `tags`, puis valide la recherche sur terme tag-only.
- PDS-97 : Câblage backend de l'expansion multilingue/synonymes dans `SearchDatasetsUseCase` (`expand_query`), propagation des termes étendus jusqu'au repository (`expanded_terms`) et exploitation côté FTS5 via clause OR. Ajout d'un test d'intégration validant `q=wetter` -> dataset taggé `meteo`.
- PDS-98 : Facettes alignées sur le scope de recherche actif (FTS + filtres), correction du filtre tag exact (JSON `json_each` + fallback CSV) pour supprimer les faux positifs de sous-chaîne. Ajout de tests d'intégration dédiés (facettes filtrées et `tag=air` vs `agriculture`).

## [1.1.3] — M10 Préparation multisource

### Added
- PDS-71 : Colonne `source` sur les 3 tables du cache — `source` (VARCHAR, NOT NULL, DEFAULT 'ckan') ajoutée aux modèles SQLAlchemy `OrganizationModel`, `DatasetModel`, `ResourceModel` et aux dataclasses domaine `Organization`, `Dataset`, `Resource`. Les upserts (`cache_repository.py`) propagent `source='ckan'`. Migration automatique `_migrate_add_source_column()` dans `create_schema()` pour les bases existantes (ALTER TABLE avec fallback si colonne déjà présente). Prépare le modèle multisource CKAN/I14Y/metadata.swiss (ADR-026).
- PDS-72 : Protocole de veille I14Y/metadata.swiss — document `Doc/20-technique/07-veille/veille-i14y-metadata-swiss.md` décrivant la fréquence de vérification (bimensuelle), les URLs à surveiller (API I14Y, handbook, GitHub, DCAT-AP), les 8 signaux de bascule (dont 4 primaires : champ ckanId, endpoint structures, bêta metadata.swiss, besoin utilisateur), les commandes curl de test API, le template de note de veille, et la procédure de réévaluation. Première vérification documentée : 2026-06-28 (S1-S4 tous absents, report confirmé ADR-026).
- PDS-74 : Mise à jour roadmap post-MVP v2.0 — refonte complète de `Doc/10-produit/03-roadmap/roadmap-mvp.md` : nouveau §0 Contexte global expliquant l'abandon CKAN, la découverte I14Y, et la stratégie 2026-2028 ; §1 Rétrospective M1-M9 avec tous les tickets livrés ; §2 M10 en cours avec tableau des tâches et justification de chaque ; §3 M11 Améliorations UX ; §4 2027 Veille et sandbox ; §5 2028 Migration metadata.swiss avec préparation déjà faite et inconnues ; §6 Timeline visuelle ASCII ; §7 Risques et mitigations. Document conçu pour servir de référence contextuelle complète même après une absence prolongée.
- PDS-76 : Page publique « Suite du projet » — nouvelle route `/suite` expliquant aux utilisateurs la transition opendata.swiss → metadata.swiss (2028). 5 sections : données actuelles (CKAN), la transition (DCAT-AP, I14Y), actions PDS-Portail, calendrier prévisionnel, ressources officielles. Nouveaux composants : molécule `Timeline` (chronologie avec marqueurs done/current/upcoming et animation pulse, conforme `--radius-none`, `prefers-reduced-motion`) et icône `ExternalLinkIcon` (SVG néo-brutaliste). Tous les liens externes annotés `aria-label="... (s'ouvre dans une nouvelle fenêtre)"` (WCAG 2.2). Liens ajoutés dans le header et le footer du layout. `make quality` 0 erreur (svelte-check 0/0, vitest 90/90, pytest 148/148, build, validate:design).

## [1.1.2] - 2026-06-27
### Added
- PDS-69 : Polish cosmétique Frontend — intégration des 6 icônes SVG néo-brutalistes (PDS-67) dans les composants : SearchIcon+FilterIcon dans FiltersPanel, DatasetIcon+CompareIcon dans CardDataset, CompareIcon dans CompareBar. Espacements aérés (`--space-*` +25%, `--line-height-body` 1.6→1.7, `--paragraph-gap` 0.75em→1em). Correction overflow texte des `<select>` dans FiltersPanel (`text-overflow: ellipsis`). Pied de page avec lien "Sébastien Schopfer" vers schopfer.moustik.site.
- Favicon « cube de données » — SVG 32×32 trois panneaux OKLCH (bleu primaire, jaune, rouge) évoquant une pile de données structurées. Remplace le logo Svelte par défaut.
- Footer enrichi — identité du portail, source opendata.swiss, lien manuel d'utilisation, crédits auteur, mentions accessibilité WCAG 2.2 AA et RGPD.
- Page `/manuel` — manuel d'utilisation complet en 6 sections (rechercher, comprendre, personnaliser, comparer, ressources, accessibilité). Lien dans le header et le footer.

### Fixed
- PDS-70 : Timeout recherche 3+ termes — l'expansion multilingue générait une explosion combinatoire de clauses LIKE (50+ termes → 200+ LIKE → timeout SQLite). Ajout d'une limite `MAX_EXPANSION_TERMS=12` dans `search_repository.py`, les termes originaux de l'utilisateur étant prioritaires (placés en tête de `all_terms`).
- PDS-70 : Index FTS5 migré vers `tokenize='unicode61 remove_diacritics 2'` (suppression automatique des accents FR/DE/IT), ajout de triggers AFTER INSERT/UPDATE/DELETE sur `datasets` pour maintenir l'index FTS5, et backfill initial au `create_schema()`.
- PDS-70 : Recherche instantanée sans bouton — le champ texte déclenche automatiquement la recherche après 400ms d'arrêt de frappe (debounce), comme sur Galaxus. Le bouton "Rechercher" est conservé en fallback (submit formulaire). `Input.svelte` forwarde désormais `oninput` et `...restProps`.
- PDS-71 : Accents français manquants dans l'interface — ~185 chaînes hardcodées sans accents dans 12 fichiers du frontend (pages, composants UI). Qualité → Qualité, Fraicheur → Fraîcheur, Completude → Complétude, resultats → résultats, jeu de donnees → jeu de données, etc. Correction syntaxique Breadcrumb (`"Fil d'Ariane"`). `svelte-check` 0 erreur, build ok.

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