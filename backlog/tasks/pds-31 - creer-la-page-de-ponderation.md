---
id: pds-31
title: Creer la page de ponderation
status: Done
assignee: []
created_date: '2026-06-13'
updated_date: '2026-06-16 23:19'
labels:
  - phase-3
  - frontend
  - qualite
  - documentation
milestone: M3 - Details dataset et qualite
dependencies:
  - PDS-15
  - PDS-16
modified_files:
  - 'frontend/src/routes/dataset/[id]/+page.svelte'
  - 'frontend/src/routes/dataset/[id]/ponderation/+page.svelte'
  - 'frontend/src/routes/dataset/[id]/ponderation/+page.ts'
  - frontend/src/test/routes/dataset-page.view.test.ts
  - frontend/src/test/routes/dataset-ponderation-page.view.test.ts
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Creer une page explicative de la ponderation des indicateurs qualite, accessible depuis la fiche dataset, pour permettre a l'utilisateur de comprendre et verifier le score.

Objectif pedagogique:
- Expliquer simplement d'ou vient le score qualite.
- Montrer les 5 composantes sans jargon inutile.
- Donner a l'utilisateur une methode concrete pour verifier chaque composante.

References: PRD-F02, PRD-NFR07, SPEC-F02, SPEC-NFR07, SPEC-002.
Sources implementation: `backlog/docs/doc-002 - references-opendata-swiss-pour-implementation.md` (sections 1 et 4).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Une page dediee explique la formule de score et les 5 composantes de ponderation.
- [x] #2 Chaque composante indique clairement comment elle est calculee et comment la verifier.
- [x] #3 La page affiche les limites d'interpretation du score (indicateur et non preuve de veracite).
- [x] #4 La fiche dataset propose un lien visible vers cette page de ponderation.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Identifier les donnees deja exposees par la fiche dataset (score, completude, fraicheur, formats, ressources).
2. Creer une nouvelle page frontend de ponderation avec structure fixe:
   - titre de page,
   - formule globale,
   - 5 blocs composantes,
   - section limites.
3. Rediger le contenu de chaque composante en 2 parties courtes:
   - "Comment c'est calcule",
   - "Comment je peux verifier".
4. Ajouter un lien visible depuis la fiche dataset vers la page de ponderation.
5. Ajouter/adapter des tests de vue pour verifier:
   - presence des sections obligatoires,
   - presence du lien depuis la fiche dataset.
6. Executer `npm run test` puis `npm run check` et reporter les resultats.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Suivi:
	- Etape 1: creer la page statique avec les sections (sans logique complexe).
	- Etape 2: connecter le lien depuis la fiche dataset.
	- Etape 3: affiner le texte pour rester clair et verifiable.
	- Etape 4: ajouter les tests.
- Regles de redaction a respecter:
	- phrases courtes,
	- vocabulaire non technique quand possible,
	- chaque composante doit inclure une action de verification concrete.
- Exemple de structure minimale d'une composante:
	- Nom de la composante.
	- Comment c'est calcule (1 a 2 phrases).
	- Comment verifier (1 a 2 phrases, source de verif explicite).
- Attention:
	- ne pas presenter le score comme une preuve de veracite,
	- ne pas modifier l'API publique des composants existants,
	- garder la navigation retour dataset/recherche intacte.

Hypothese implementation: la page de ponderation est informative et statique (sans nouvel appel API), routee en /dataset/:id/ponderation, avec retour explicite vers la fiche dataset et la recherche.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implementation PDS-31 terminee avec scope strict frontend.

Realise:
- Ajout d une route dediee de ponderation en /dataset/:id/ponderation.
- Creation d une page explicative contenant:
  - section Formule du score,
  - 5 sections Composante avec "Comment c est calcule" et "Comment je peux verifier",
  - section Limites d interpretation en langage simple.
- Ajout d un lien visible depuis la fiche dataset vers la page de ponderation.
- Ajout/ajustement des tests de vue pour couvrir:
  - presence du lien de ponderation depuis la fiche dataset,
  - presence des sections obligatoires de la page de ponderation,
  - navigation retour dataset/recherche.

Validation:
- npm run test: OK (56/56)
- npm run check: OK (0 erreur, 0 warning)

Contrainte respectee:
- Aucun changement d API publique backend.
- Navigation existante preservee (retours dataset/recherche).
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Une route frontend dediee est creee pour la page de ponderation et elle est accessible depuis la fiche dataset.
- [x] #2 La page contient une section "Formule du score" et 5 sections "Composante" avec calcul + verification.
- [x] #3 La page contient une section "Limites d'interpretation" en langage simple.
- [x] #4 Le contenu est lisible en mobile et ne casse pas la navigation existante.
- [x] #5 Les controles frontend (`npm run test`, `npm run check`) sont executes ou explicitement justifies si indisponibles.
<!-- DOD:END -->
