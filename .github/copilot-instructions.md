# PDS-Portail - Instructions Copilot

Ces instructions sont pour GitHub Copilot.

## 1) Priorites de travail

1. Stabilite et fiabilite avant vitesse.
2. Changements minimaux et testables.
3. Respect strict de l'architecture hexagonale:
- domain = logique metier pure
- application = use cases + ports
- infrastructure = adapters externes/persistence
- presentation = API/DTO

## 2) Contexte projet

- Nom: PDS-Portail - Explorateur Open Data Suisse
- Stack backend: Python + FastAPI + SQLite + ingestion CKAN
- Stack frontend: SvelteKit 5
- Documentation source: Doc/ et backlog/
- Sprint actif: M11 (monetisation), M10 termine

## 3) Workflow obligatoire avant implementation

1. Identifier la tache backlog active (PDS-XX).
2. Lire la SPEC et les ADR lies.
3. Lire seulement les fichiers utiles a la modification.
4. Proposer le plus petit patch possible.

## 4) Qualite et validations

Avant de conclure un changement code, executer les validations pertinentes.

Backend:
- uv run black --check app/ tests/
- uv run ruff check app/ tests/
- uv run mypy app/ tests/
- uv run pytest --cov=app --cov-fail-under=80

Frontend:
- cd frontend && npx svelte-check
- cd frontend && npm run test
- cd frontend && npm run build
- cd frontend && npm run validate:design

Commande globale:
- make quality

## 5) Regles de code

- Commentaires explicites en francais quand necessaire.
- Eviter les refactors larges non demandes.
- Ne pas coupler les tests a des details d'implementation fragiles.
- Favoriser des assertions comportementales fortes.
- Eviter l'etat global implicite dans les tests.
- Eviter les dependances temporelles non controlees (datetime.now sans controle en test).

## 6) Regles documentation et tracabilite

- Toute tache PDS completee doit laisser une trace documentaire coherente:
- backlog/tasks
- backlog/docs si rapport
- Doc/20-technique/01-spec si evolution technique notable
- Doc/30-decisions/adr si decision structurante
- Doc/40-exploitation si impact runbook/exploitation

- Prefixer les resumes et le CHANGELOG avec le ticket actif: PDS-XX

## 7) Accessibilite et UI (non negociable)

- WCAG 2.2 AA minimum
- Contraste 4.5:1 minimum
- Navigation clavier complete
- ARIA explicite sur composants interactifs
- Pas de dependance CDN externe
- Tokens couleurs en OKLCH dans le frontend

## 8) Securite

- Respecter CSP frontend stricte
- Respecter le rate-limiting backend
- Respecter timeout CKAN
- Ne jamais introduire de mock actif en production

## 9) Fichiers et zones sensibles

- Eviter les modifications hors perimetre de la tache.
- Ne pas modifier des fichiers de backlog/documentation non lies sans raison explicite.
- En cas de doute sur un changement potentiellement destructif, demander confirmation.

## 10) Sortie attendue de Copilot

- Expliquer ce qui a ete change et pourquoi.
- Donner les preuves de validation executees.
- Lister les risques residuels.
- Proposer les prochaines etapes uniquement si elles sont naturelles.
