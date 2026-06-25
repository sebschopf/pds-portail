# PDS-Portail

Explorateur accessible de données publiques suisses basé sur un frontend SvelteKit et un backend FastAPI.

Le produit permet à toute personne, sans bagage technique, de trouver des datasets opendata.swiss, d'évaluer leur qualité et d'explorer leur contenu en langage simple, sans manipuler l'API CKAN directement.

## Architecture

```
┌─────────────────────┐     HTTP/JSON     ┌─────────────────────┐
│  FRONTEND (Vercel)  │ ◄──────────────►  │  BACKEND (Fly.io)   │
│  SvelteKit 5        │                   │  Python + FastAPI   │
│  Recherche, détail, │                   │  API REST v1        │
│  qualité, ressources│                   └─────────┬───────────┘
└─────────────────────┘                             │
                                                    ▼
                                             ┌─────────────┐
                                             │  SQLite     │
                                             │  Cache (1GB)│
                                             └─────────────┘
```

- **Frontend** : SvelteKit 5 + Svelte 5 runes — déployé sur Vite/Vercel
- **Backend** : Python 3.12 + FastAPI + SQLAlchemy — déployé sur Fly.io (cdg)
- **Cache** : SQLite sur volume persistant (1 GB, snapshots automatiques)
- **Source** : API CKAN opendata.swiss (métadonnées publiques)

## Pré-requis

- **Python** >= 3.11 (recommandé 3.12)
- **Node.js** >= 22
- **uv** (gestionnaire Python) : `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **npm** (inclus avec Node.js)

## Setup rapide

### 1. Backend

```sh
# Cloner et installer les dépendances
git clone git@tangled.org:did:plc:nbr4gz4cedmnw2jizmjsuspr && cd pds-portail
uv sync --frozen

# Copier la configuration
cp .env.example .env

# Lancer le serveur (port 8000 par défaut)
uv run uvicorn app.main:app --reload
```

Vérifier : `curl http://127.0.0.1:8000/api/v1/health`

### 2. Frontend

```sh
cd frontend
npm ci
npm run dev
```

Ouvrir `http://localhost:5173`.

### 3. Mode mock (sans backend)

```sh
cd frontend
npm run dev:mock
```

> **Interdit en production** — le build échoue si `PUBLIC_USE_MOCK_API=1` avec `NODE_ENV=production`.

## Qualité

Avant chaque commit, exécuter la commande suivante à la racine du projet :

```sh
make quality
```

Cela lance toute la chaîne qualité :

- **Backend** : format (black), lint (ruff), types (mypy), tests (pytest --cov-fail-under=80)
- **Frontend** : Svelte check, tests (vitest), build, validation design system

Pour exécuter la qualité sur une seule partie :

```sh
make quality-backend   # Backend uniquement
make quality-frontend  # Frontend uniquement
```

## Déploiement

### Frontend — Vercel

1. Connecter le dépôt Git à Vercel (intégration Git).
2. Configurer :
   - **Root directory** : `frontend`
   - **Build command** : `npm run build`
   - **Output directory** : `.svelte-kit/output`
3. Définir les variables d'environnement :
   - `PUBLIC_API_BASE_URL` : `https://pds-portail-backend.fly.dev`
   - `PUBLIC_USE_MOCK_API` : **ne pas définir** (interdit en production)
4. Vercel détecte automatiquement `@sveltejs/adapter-auto`.

### Backend — Fly.io

1. Installer flyctl : `curl -L https://fly.io/install.sh | sh`
2. Déployer : `flyctl deploy` (utilise `Dockerfile` + `fly.toml` à la racine)
3. Volume persistant créé une fois : `flyctl volumes create pds_portail_cache --region cdg --size 1`
4. Variables d'environnement définies dans `fly.toml` (section `[env]`)
5. URL : `https://pds-portail-backend.fly.dev`

### CI — Pipeline local

Le fichier `.github/workflows/ci.yml` est destiné à GitHub Actions. Si le dépôt est déplacé vers GitHub, la CI s'exécutera automatiquement sur chaque push/PR. Actuellement sur Tangled, la qualité est vérifiée manuellement via les commandes ci-dessus.

## Variables d'environnement

### Backend (.env)

| Variable | Défaut | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/app.db` | URL de la base de données (prod Fly.io: `sqlite:////var/data/app.db`) |
| `CKAN_BASE_URL` | `https://opendata.swiss` | API CKAN source |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Origines autorisées (prod: Vercel) |
| `EXPOSE_API_DOCS` | `true` | `/docs`, `/redoc`, OpenAPI (false en prod) |

### Frontend (.env.local)

| Variable | Dev | Prod |
|---|---|---|
| `PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | `https://pds-portail-backend.fly.dev` |
| `PUBLIC_USE_MOCK_API` | absent ou `1` (dev:mock) | **interdit** |

## Exploitation

### Monitoring

- **Backend** : logs accessibles via `flyctl logs` ou le dashboard Fly.io.
- **Health check** : `GET /api/v1/health` répond `{"status":"ok","last_sync":"..."}`.
- **Frontend** : pas de tracker tiers (conformité RGPD). Les erreurs sont visibles dans la console navigateur.

### Rollback

- **Frontend** : Vercel permet de déployer une version antérieure (Deployments → ... → Promote to Production).
- **Backend** : Fly.io permet de revenir à une version précédente (`flyctl deploy --image <previous>` ou dashboard → Machines → redeploy older version).

### Cache

Le cache SQLite persiste sur un volume Fly.io (1 GB) monté sur `/var/data`. Les snapshots automatiques (rétention 5 jours) protègent contre la perte de données. En local, il persiste dans `data/app.db`.

L'ingestion CKAN est incrémentale : bootstrap au démarrage si cache vide, puis 1000 datasets par cycle horaire. Une fois le catalogue complet chargé (~10h), le mode différentiel s'active automatiquement (seuls les datasets modifiés depuis la dernière synchro sont récupérés, via `fq=metadata_modified`).

Endpoints de supervision : `GET /api/v1/internal/sync/status` (offset courant), `POST /api/v1/internal/sync` (forcer un cycle).

## Projet

- **État** : MVP deploye en production ; travail en cours sur M6/M7 avec contraintes d'exploitation reelles
- **Dépôt** : [Tangled](https://tangled.org/moustik.tngl.sh/pds-portail) · [GitHub Mirror](https://github.com/sebschopf/pds-portail)
- **Backend** : https://pds-portail-backend.fly.dev
- **Frontend** : https://pds-portail.vercel.app

## Documentation

La documentation complète du projet est dans le dossier `Doc/`. Voir [`Doc/README.md`](Doc/README.md) pour l'index complet.

### Lectures essentielles

| Document | Description |
|---|---|
| [Discovery Brief](Doc/10-produit/01-cadrage/discovery-brief.md) | Probleme, opportunite, personas, criteres de succes |
| [PRD](Doc/10-produit/02-prd/prd.md) | Objectifs produit, exigences fonctionnelles, non-scope |
| [SPEC-001 Architecture](Doc/20-technique/01-spec/spec-001-technical-architecture.md) | Architecture technique, stack, decisions |
| [SPEC-003 Multilingue](Doc/20-technique/01-spec/spec-003-recherche-multilingue-synonymes.md) | Recherche multilingue FR/DE/IT/EN et synonymes metier |
| [ADR-001 a ADR-025](Doc/30-decisions/adr/) | Toutes les decisions architecturales justifiees |
| [Diagramme de flux](Doc/20-technique/01-spec/diagramme-flux-donnees.md) | Diagrammes Mermaid des flux de donnees |
| [Glossaire](Doc/20-technique/03-glossaire/glossaire.md) | Tous les termes techniques en langage accessible |
| [Modele de menaces](Doc/20-technique/04-securite/modele-de-menaces.md) | Surface d'attaque, menaces, protections |
| [Procedure d'exploitation](Doc/20-technique/02-exploitation/procedure-exploitation.md) | Runbooks, monitoring, rollback |
| [Guide utilisateur](Doc/10-produit/04-support/guide-utilisateur.md) | Documentation utilisateur du produit |
