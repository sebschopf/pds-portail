---
id: PDS-87
title: 'PDS-87: Backend — Use case de détection des changements d''état'
status: Done
assignee: []
created_date: '2026-06-28 21:22'
labels:
  - backend
  - premium
  - detection
  - surveillance
milestone: m-11
dependencies:
  - PDS-86
documentation:
  - Doc/20-technique/01-spec/spec-009-service-payant-surveillance-changements.md
priority: high
ordinal: 27200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implémenter le use case de détection des changements d'état exécuté après chaque cycle d'ingestion CKAN (SPEC-009 §3.1).

Backend :
1. Créer le use case `DetectChangesUseCase` dans `app/application/use_cases/` :
   - Dépendances : `WatcherRepositoryPort`, `ChangeLogRepositoryPort`, `CacheReadRepositoryPort`.
   - Méthode `execute()` :
     a. Récupérer tous les `watched_datasets` groupés par dataset_id.
     b. Pour chaque dataset_id, récupérer le dataset depuis le cache.
     c. Comparer `metadata_modified` avec `last_known_metadata_modified`.
     d. Comparer le nombre de ressources (`len(dataset.resources)`) avec `last_known_resource_count`.
     e. Recalculer le score de qualité via `compute_indicators()` (déjà dans `domain/quality_indicators.py`).
     f. Pour chaque ressource, faire un HEAD request sur l'URL (timeout 5s) pour vérifier l'intégrité.
     g. Si un changement est détecté, insérer dans `change_log`.
     h. Mettre à jour les `last_known_*` dans `watched_datasets`.

2. Intégration dans `RunSyncCycleUseCase` (existant) :
   - Après l'appel à `SyncCkanBatchUseCase.execute()`, appeler `DetectChangesUseCase.execute()`.
   - Injecter `DetectChangesUseCase` dans le constructeur de `RunSyncCycleUseCase`.

3. Types de changements :
   - `metadata_updated` : metadata_modified a changé.
   - `resource_added` : nouveau nombre > ancien.
   - `resource_removed` : nouveau nombre < ancien.
   - `quality_degraded` : score qualité en baisse de plus de 5 points.
   - `link_broken` : HEAD request retourne statut >= 400 ou timeout.

Références : SPEC-009 §3.1, dépendance PDS-86.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 La détection compare `metadata_modified` du dataset CKAN avec `last_known_metadata_modified` et log un changement si différent
- [x] #2 La détection compare le nombre de ressources actuelles avec `last_known_resource_count` et log resource_added/resource_removed
- [x] #3 La détection recalcule le score de qualité via `compute_indicators()` et compare avec `last_known_quality_score`
- [x] #4 La détection vérifie l'intégrité des URLs de ressources (HEAD request via httpx) et log link_broken si statut >= 400
- [x] #5 Chaque changement est inséré dans `change_log` avec change_type, previous_value, new_value, detected_at
- [x] #6 Les valeurs `last_known_*` dans `watched_datasets` sont mises à jour après détection
- [x] #7 Le use case est intégré à `RunSyncCycleUseCase` (exécuté après chaque cycle d'ingestion)
- [x] #8 Tests pytest : metadata modifié, ressource ajoutée, ressource supprimée, qualité dégradée, lien cassé, aucun changement
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Validation executee ou explicitement notee si indisponible
- [x] #2 Documentation synchronisee si la tache modifie le comportement ou les choix
- [x] #3 Tracabilite PRD, SPEC et ADR preservee
- [ ] #4 Preuves d'exploitation archivees si la tache touche deploiement, fiabilite ou incident
- [ ] #5 Pour toute correction prod/exploitation: changelog et tache backlog mis a jour, doc d'exploitation synchronisee si necessaire
<!-- DOD:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
- `DetectChangesUseCase` compare metadata, volume de ressources, score qualité et état des liens sur les datasets surveillés.
- `RunSyncCycleUseCase` déclenche la détection en fin de cycle via injection explicite.
- Tests ciblés ajoutés pour les 5 types de changements et le cas sans changement.
<!-- SECTION:FINAL_SUMMARY:END -->
