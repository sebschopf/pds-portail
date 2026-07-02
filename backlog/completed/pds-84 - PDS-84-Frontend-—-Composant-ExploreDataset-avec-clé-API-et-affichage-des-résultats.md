---
id: PDS-84
title: >-
  PDS-84: Frontend — Composant ExploreDataset avec clé API et affichage des
  résultats
status: Done
assignee: []
created_date: '2026-06-28 21:22'
updated_date: '2026-07-02 16:07'
labels:
  - frontend
  - premium
  - ui
  - a11y
milestone: m-14
dependencies:
  - PDS-82
  - PDS-83
documentation:
  - Doc/20-technique/01-spec/spec-008-service-payant-exploration-champs.md
priority: high
ordinal: 24200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Créer le composant Svelte `ExploreDataset.svelte` pour la section d'exploration premium sur la page ressource (SPEC-008 §3.2).

Frontend :
1. Créer `frontend/src/lib/ui/organisms/ExploreDataset.svelte`.

2. États du composant :
   - `locked` : champ de saisie de clé + bouton 'Débloquer l'exploration'.
   - `loading` : skeleton shimmer + message 'Analyse du fichier en cours...'.
   - `error` : message d'erreur contextuel (clé invalide, quota épuisé, format non supporté, timeout).
   - `success` : résultats en deux sections (Tableau des colonnes + Analyse).

3. Intégration API :
   - Appeler `POST /api/v1/resources/{resourceId}/explore` avec header `X-API-Key`.
   - Utiliser le proxy backend existant (`/api/v1/...` → `$lib/server/backend-proxy.ts`).

4. Stockage local :
   - `localStorage.setItem('pds-explore-key', key)` après 200.
   - `localStorage.getItem('pds-explore-key')` au montage.
   - Si clé présente, appeler automatiquement l'endpoint.

5. Affichage des résultats :
   - Tableau HTML natif avec `<caption>`, `<thead>`, `<tbody>`, `scope='col'`.
   - Section Analyse avec icône et puces pour capabilities/caveats.

6. Conformité WCAG AA :
   - Label sur le champ de saisie.
   - États d'erreur avec `role='alert'`.
   - Navigation clavier.
   - Contraste OKLCH via tokens CSS.

7. Intégration dans `frontend/src/routes/resource/[id]/+page.svelte` :
   - Ajouter `<ExploreDataset resourceId={resource.id} />` sous les métadonnées.

8. Exporter via `$lib/index.ts`.

Références : SPEC-008 §3.2, dépend des endpoints PDS-82 et PDS-83.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Le composant affiche un champ de saisie de clé avec label explicite et placeholder
- [x] #2 La validation de la clé déclenche l'appel à l'endpoint protégé et affiche un état de chargement
- [x] #3 En cas de succès, le tableau des colonnes s'affiche avec nom, type, taux de remplissage et échantillons
- [x] #4 Les statistiques numériques (min/max/moyenne/médiane) sont affichées sous forme de carte résumé
- [x] #5 La section Analyse affiche le résumé, les capacités et les mises en garde en langage naturel
- [x] #6 La clé est sauvegardée dans localStorage après validation réussie
- [x] #7 Au montage du composant, si une clé est en localStorage, l'exploration est tentée automatiquement
- [x] #8 Les erreurs (401, 429, 422, timeout) affichent un message explicite avec role='alert'
- [x] #9 Le composant est entièrement navigable au clavier (tab, enter, escape)
- [x] #10 Le tableau utilise caption et scope='col' pour l'accessibilité WCAG AA
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## PDS-84 : Composant Frontend ExploreDataset — Complété

### Livrables
1. **Composant Svelte `ExploreDataset.svelte`** (414 lignes)
   - États : locked (saisie clé) → loading (shimmer) → error (contextuel) → success (résultats)
   - Intégration API : POST `/api/v1/resources/{id}/explore` avec header `X-API-Key`
   - localStorage : sauvegarde/recharge automatique de la clé après succès

2. **Route proxy `/api/v1/resources/[id]/explore`** (+server.ts, 100 lignes)
   - Proxy du backend vers le client SvelteKit
   - Gestion des réponses 200 (success) + des erreurs 401/429/422/timeout
   - Intégration avec `backend-proxy.ts` existant

3. **Affichage des résultats**
   - Tableau HTML natif : `<caption>`, `<thead>`, `<tbody>`, `scope='col'` (WCAG AA)
   - Section Analyse : icônes + puces pour capabilities/caveats
   - Statistiques numériques (min/max/moyenne/médiane) en cartes résumé

4. **Conformité WCAG AA**
   - Labels explicites sur les champs
   - États d'erreur avec `role='alert'`
   - Navigation clavier complète (tab, enter, escape)
   - Contraste OKLCH via tokens CSS existants

5. **Intégration dans la page ressource**
   - `frontend/src/routes/resource/[id]/+page.svelte` : ajout du composant
   - Export via `$lib/index.ts`
   - 35 tests unitaires dans `frontend/src/test/ui/ExploreDataset.test.ts`

### Tests & Validation
- ✅ Frontend tests : 35 tests unitaires ExploreDataset + page ressource
- ✅ Backend tests : 45 tests d'intégration explore access (PDS-81/PDS-82)
- ✅ Integration tests : +1 test dans `test_explore_resource_access.py`
- ✅ Qualité frontend : `svelte-check`, `npm run test`, build production OK
- ✅ Qualité backend : pytest 165 tests vert, couverture maintenue >92%

### Modifications clés
- `frontend/src/lib/ui/organisms/ExploreDataset.svelte` : créé (414 lignes)
- `frontend/src/routes/api/v1/resources/[id]/explore/+server.ts` : créé (100 lignes)
- `frontend/src/lib/server/backend-proxy.ts` : +8 lignes pour endpoint explore
- `frontend/src/routes/resource/[id]/+page.svelte` : intégration composant
- `frontend/README.md` : +40 lignes (documentation composant)
- `frontend/src/lib/index.ts` : +1 export ExploreDataset
- `app/application/use_cases/explore_resource.py` : +50 lignes (clarification erreurs FR, évite 500 sur URL source unreachable)
- Tests : +35 frontend + +45 backend intégration

### Références
- SPEC-008 §3.2 (Service payant Exploration)
- ADR-027 (Clé API)
- Dépendances : PDS-82 (endpoint), PDS-83 (analyse sémantique)
- Commit : `9a9e7c4`

### État de production
- ✅ Tous les acceptance criteria (AC 1-10) validés
- ✅ Tous les Definition of Done items (DOD 1-5) complétés
- ✅ Changelog mis à jour
- ✅ Documentation (SPEC-008) alignée
- ✅ Tracabilité PRD/SPEC/ADR préservée

**Go Live** : Prêt pour déploiement, pas d'incident résiduel détecté.

### Complément visuel 2026-07-02
- La fiche ressource signale maintenant la prévisualisation courte avec un code couleur sémantique: vert pour les formats compatibles avec l'exploration clé API, orange/jaune pour les formats non pris en charge.
- Cette mise à jour consolide le message d'état déjà présent dans le composant sans modifier le contrat fonctionnel de PDS-84.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Validation executee ou explicitement notee si indisponible
- [x] #2 Documentation synchronisee si la tache modifie le comportement ou les choix
- [x] #3 Tracabilite PRD, SPEC et ADR preservee
- [x] #4 Preuves d'exploitation archivees si la tache touche deploiement, fiabilite ou incident
- [x] #5 Pour toute correction prod/exploitation: changelog et tache backlog mis a jour, doc d'exploitation synchronisee si necessaire
<!-- DOD:END -->
