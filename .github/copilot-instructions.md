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
- SOLID et SRP
- Code as simple as possible, mais pas plus simple.
- Code as documented as possible, mais pas plus verbeux.

## 5b) Politique de Test (SPEC-011 § 9)

**Référence obligatoire :** `Doc/20-technique/01-spec/spec-011-fiabilisation-suite-tests-backend.md` (section 9)

Tout test doit respecter :
- **Nommage** : `test_<method>_<scenario>_<expected>`, fixtures `lowercase_with_underscores`
- **Structure** : Arrange/Act/Assert claire
- **Isolation** : chaque test indépendant, pas d'ordre-dépendance
- **Déterminisme** : pas de `datetime.now()`, pas de sleep, fixtures avec scope function
- **Assertions comportementales** : testent l'effet métier (ex: `license.used_this_month: 0→1`)
- **Fixtures SOLID/SRP** : une responsabilité par fixture, réutilisables
- **Couverture cible** par module critique : app/main.py ≥90%, dependencies.py 100%, etc.

Checklist pré-soumission : voir SPEC-011 § 9.7

Exécution : voir R004 § 3-5 (sequence, checklist, incident response)

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

## 11) Maillage de la Documentation (Navigation Rapide)

Quand tu cherches une information, utilise ce maillage pour trouver rapidement :

### 11.1 Par Type de Question

**"Comment implémenter une feature ?"**
→ SPEC-NNN (`Doc/20-technique/01-spec/spec-*.md`)
→ backlog/tasks/PDS-XX (description + dépendances)
→ Exemples concrets dans le code

**"C'est quel choix d'architecture ?"**
→ ADR-NNN (`Doc/30-decisions/adr/`) - justification complète
→ SPEC-NNN section "Dépendances/Références" pour le lien

**"Comment tester mon code ?"**
→ SPEC-011 § 9 (politique de test)
→ R004 § 3-5 (exécution, checklist)
→ backlog/tasks/test_*.py (exemples du projet)

**"Quel est le runbook exploitation ?"**
→ R00N (`Doc/40-exploitation/R*.md`)
→ backlog/docs/RAPPORT-*.md pour les données brutes

**"Quels modules sont critiques ?"**
→ SPEC-011 § 9.6 (cibles de couverture par module)
→ backlog/docs/RAPPORT-QA-PDS-108 (métriques actuelles)

### 11.2 Index par Domaine

**Authentification & Sécurité :**
- ADR-027 (clé API exploration) → SPEC-008 § 3 → PDS-80/81
- ADR-030 (magic tokens surveillance) → SPEC-009 § 3 → PDS-92

**Paiement & Licensing :**
- ADR-028 (Polar Stripe) → SPEC-009 § 2 → PDS-85
- SPEC-008 § 3.1 (table licenses) → PDS-81

**Exploration (Premium Feature) :**
- SPEC-008 § 3-4 (endpoint, parsing, analyse sémantique)
- ADR-027 (clé API) → ADR-028 (paiement) → ADR-031 (tests)
- PDS-81 (licence), PDS-82 (parsing), PDS-83 (analyse)

**Surveillance (Premium Feature) :**
- SPEC-009 (détection changements, alertes email)
- ADR-028 (paiement), ADR-029 (emails), ADR-030 (tokens)
- PDS-86 (tables), PDS-87 (détection), PDS-88 (emails), PDS-89 (webhooks)

**Fiabilisation Tests :**
- SPEC-011 § 9 (politique) + R004 (opérationnel)
- PDS-105 (stabilisation integration)
- PDS-106 (couverture critique)
- PDS-107 (anti-flaky)
- PDS-108 (métriques)

### 11.3 Parcours Communs

**Je dois implémenter une route API protégée :**
1. Lire ADR-027 (pourquoi clé API)
2. Lire SPEC-008 § 3 (structure endpoint)
3. Lire PDS-81 (comment require_license marche)
4. Lire SPEC-011 § 9 (comment tester)
5. Code → validation → tests

**Je dois ajouter un test pour une use case :**
1. Lire SPEC-011 § 9 (standards d'écriture)
2. Lire R004 § 6.1 (anti-flaky patterns)
3. Copier fixture pattern de backlog/tasks/test_explore_resource.py
4. Écrire test → checklist pré-soumission (SPEC-011 § 9.7)

**Je dois faire une décision architecturale :**
1. Chercher ADR existante sur le sujet
2. Lire les options considérées et rejetées
3. Voir la décision justifiée
4. Si modification : ADR-NNN (nouveau) → traçabilité SPEC/backlog

## 12) MCPs & Tools Disponibles

### 12.1 MemPalace (Knowledge Graph & Memory)

Outils pour persister et retrouver des infos dans la "palace" (graphe de connaissance) :

**Drawer Filing (content storage) :**
- `mcp_mempalace_mempalace_add_drawer` : File du contenu verbatim dans une drawer
  - Paramétre wing: projet, room: aspect (backend, decisions, meetings)
  - Utilisé pour : sauvegarder extraits de specs, décisions, appels
- `mcp_mempalace_mempalace_check_duplicate` : Vérifie si contenu déjà en palace (évite duplication)
- `mcp_mempalace_mempalace_delete_drawer` : Supprime une drawer (irréversible)

**Semantic Search :**
- `mcp_mempalace_mempalace_search` : Recherche sémantique (par similarité, pas regex)
  - Util pour : trouver décisions passées, patterns, contexte ancien
  - Paramètres : query (keywords), room/wing (filtrer), max_distance (sévérité)

**Diary & Session Notes :**
- `mcp_mempalace_mempalace_diary_write` : Écrit entrée diary en format AAAK compressé
- `mcp_mempalace_mempalace_diary_read` : Lit diary entries récentes

**Knowledge Graph :**
- `mcp_mempalace_mempalace_kg_invalidate` : Marque un fait comme plus valide (ex: "job ended")

**Utilité pour ce projet :**
- Garder un index des décisions prises et pourquoi
- Persister des découvertes complexes (ex: patterns ReloadModules → PDS-105)
- Retrouver rapidement contexte ancien si regression

### 12.2 Subagents

**Explore Agent** : agent de recherche codebase rapide, read-only
- Utiliser pour explorer structure avant de modifier
- Paramètres : `thoroughness=quick|medium|thorough`
- Utilisé pour : comprendre codebase, trouver patterns, valider hypothèses avant implémentation

Exemple : avant PDS-81, lancer subagent "Explore infrastructure licence existante"

### 12.3 File & Code Tools

**File Search & Read :**
- `file_search` : trouve fichiers par pattern glob
- `read_file` : lit contenu (spécifier range de lignes pour éviter tokens)
- `grep_search` : recherche texte dans fichiers (regex supportée)

**Edit & Create :**
- `replace_string_in_file` : édite fichier (fournir 3-5 lignes contexte)
- `multi_replace_string_in_file` : édite plusieurs fichiers en parallèle (efficacité)
- `create_file` : crée nouveau fichier

**Préférence :** 
- Lire large range (100+ lignes) plutôt que nombreuses petites lectures
- Faire édits en parallèle avec `multi_replace_string_in_file`
- Privilégier `grep_search` pour overview fichier avant `read_file`

### 12.4 Terminal Execution

**Run Commands :**
- `run_in_terminal` : exécute commande shell, retourne output
- Mode `sync` (défaut) : attend completion, retourne full output
- Mode `async` : retourne terminal ID, continue running (pour serveurs)

**Utilisé pour :**
- `make quality-backend` (tous les checks : black, ruff, mypy, pytest)
- `uv run pytest` (tests spécifiques)
- `uv run black/ruff` (formatting & linting)

### 12.5 VS Code Integration

**Language Server (Pylance) :**
- `activate_pylance_import_analysis_tools` : analyse imports et modules installés
- `activate_pylance_environment_management_tools` : gère Python environments
- `mcp_provides_tool_pylanceDocString` : récupère docstring de symbole

**Utilité :** diagnostiquer imports missing, vérifier types, documenter API

### 12.6 Notes Pratiques

**Quand lancer un Subagent ?**
- Avant PDS : explorer infrastructure existante, valider hypothèses
- Quand lost : "que font les tests pour module X ?"
- Quand cherche pattern : "montre-moi les use cases qui font ça"

**Quand utiliser MemPalace ?**
- Après découverte importante : `mcp_mempalace_mempalace_add_drawer` → wing project, room decisions
- Quand regression suspecte : `mcp_mempalace_mempalace_search` → retrouver décision passée
- Session multipart : `mcp_mempalace_mempalace_diary_write` → noter progrès, blockers, learnings

**Quand privilégier grep vs. file_search ?**
- `grep_search` : si tu cherches par contenu (regex, mots-clés)
- `file_search` : si tu cherches par nom/pattern fichier (glob)
