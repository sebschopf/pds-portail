# Changelog - PDS-Portail

Toutes les modifications notables de ce projet seront documentées dans ce fichier.
Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/) et ce projet respecte le [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] (En cours - Milestones M6 & M7)
### Added (Ajouts)
- PDS-40 : Recherche différenciante avec ranking hybride explicable et mise en avant de la pertinence (M6).
- PDS-41 : Recherche multilingue FR/DE/IT/EN — dictionnaire 20 concepts × 4 langues, 15 concepts de synonymes métier, expansion de requête traçable intégrée au pipeline de recherche (M6).
- PDS-42 : Affichage du "Pourquoi ce résultat" dans les cartes de recherche et refonte de la page pondération (M6).
- PDS-43 : Comparaison guidée de datasets — sélection de 2 à 4 datasets depuis la recherche, tableau comparatif avec badges de qualité colorés (OKLCH sémantique), vue desktop/mobile responsive, endpoint batch optimisé (1 seul round-trip DB) (M6).
- PDS-47 : Instrumentation KPI de base pour le Time-to-first-relevant-dataset (M7, planifié).
- PDS-50 : Documentation technique — glossaire (27 termes), diagramme de flux Mermaid, modèle de menaces (6 menaces, trust boundaries), section Documentation dans le README.
- PDS-51 : Mise en conformité Svelte 5 best practices — `app.html` lang="fr", suppression meta non standard, `onMount` → `$effect`, titres de page uniques sur les 4 pages.
- PDS-52 : Ingestion CKAN incrémentale avec suivi d'offset persistant — table `sync_state`, reprise après redéploiement, endpoints `POST /api/v1/internal/sync` et `GET /api/v1/internal/sync/status` (M7).
- Gouvernance d'ouverture de session en mode production : lecture courte obligatoire, ancrage backlog/SPEC/ADR, validation ciblée et traçabilité d'exploitation.

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
- Exposition de l'API Docs désactivée en production (`EXPOSE_API_DOCS=false`).