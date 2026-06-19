# PDS-Portail

Explorateur accessible de données publiques suisses basé sur un frontend SvelteKit et un backend FastAPI.

Le produit permet à toute personne, sans bagage technique, de trouver des datasets opendata.swiss, d'évaluer leur qualité et d'explorer leur contenu en langage simple, sans manipuler l'API CKAN directement.

## Architecture

```
┌─────────────────────┐     HTTP/JSON     ┌─────────────────────┐
│  FRONTEND (Vercel)  │ ◄──────────────►  │  BACKEND (Render)   │
│  SvelteKit 5        │                   │  Python + FastAPI   │
│  Recherche, détail, │                   │  API REST v1        │
│  qualité, ressources│                   └─────────┬───────────┘
└─────────────────────┘                             │
                                                    ▼
                                             ┌─────────────┐
                                             │  SQLite     │
                                             │  Cache      │
                                             └─────────────┘
```

- **Frontend** : SvelteKit 5 + Svelte 5 runes — déployé sur Vite/Vercel
- **Backend** : Python 3.12 + FastAPI + SQLAlchemy — déployé sur Render
- **Cache** : SQLite locale (fichier, intégrée au backend)
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
   - `PUBLIC_API_BASE_URL` : URL du backend Render
   - `PUBLIC_USE_MOCK_API` : **ne pas définir** (interdit en production)
4. Vercel détecte automatiquement `@sveltejs/adapter-auto`.

### Backend — Render

1. Connecter le dépôt Git à Render en tant que **Web Service**.
2. Configurer :
   - **Start command** : `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}`
   - **Health check** : `/api/v1/health`
3. Définir les variables d'environnement :
   - `DATABASE_URL` : `sqlite:///./data/app.db`
   - `CKAN_BASE_URL` : `https://opendata.swiss`
   - `CORS_ALLOWED_ORIGINS` : URL du frontend Vercel
   - `EXPOSE_API_DOCS` : `false`
   - `PYTHON_VERSION` : `3.12`

### CI — Pipeline local

Le fichier `.github/workflows/ci.yml` est destiné à GitHub Actions. Si le dépôt est déplacé vers GitHub, la CI s'exécutera automatiquement sur chaque push/PR. Actuellement sur Tangled, la qualité est vérifiée manuellement via les commandes ci-dessus.

## Variables d'environnement

### Backend (.env)

| Variable | Défaut | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/app.db` | URL de la base de données |
| `CKAN_BASE_URL` | `https://opendata.swiss` | API CKAN source |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Origines autorisées (prod: Vercel) |
| `EXPOSE_API_DOCS` | `true` | `/docs`, `/redoc`, OpenAPI (false en prod) |

### Frontend (.env.local)

| Variable | Dev | Prod |
|---|---|---|
| `PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | URL Render cible |
| `PUBLIC_USE_MOCK_API` | absent ou `1` (dev:mock) | **interdit** |

## Exploitation

### Monitoring

- **Backend** : logs accessibles via le dashboard Render.
- **Health check** : `GET /api/v1/health` répond `{"status":"ok","last_sync":"..."}`.
- **Frontend** : pas de tracker tiers (conformité RGPD). Les erreurs sont visibles dans la console navigateur.

### Rollback

- **Frontend** : Vercel permet de déployer une version antérieure (Deployments → ... → Promote to Production).
- **Backend** : Render permet de revenir à un déploiement précédent (Dashboard → Deploys → Rollback).

### Cache

Le cache SQLite est réinitialisé à chaque redémarrage du backend sur Render (fichier éphémère). En local, il persiste dans `data/app.db`. L'ingestion CKAN se fait au démarrage et toutes les heures (CRON interne). À migrer vers PostgreSQL post-MVP si nécessaire.

## Projet

- **État** : MVP en phase 5 (déploiement, QA, documentation)
- **Dépôt** : [Tangled](https://tangled.org/moustik.tngl.sh/pds-portail) · [GitHub Mirror](https://github.com/sebschopf/pds-portail)
- **Backend** : https://pds-portail-backend.onrender.com
- **Frontend** : https://pds-portail.vercel.app
