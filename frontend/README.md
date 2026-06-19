# sv

Everything you need to build a Svelte project, powered by [`sv`](https://github.com/sveltejs/cli).

## Creating a project

If you're seeing this, you've probably already done this step. Congrats!

```sh
# create a new project
npx sv create my-app
```

To recreate this project with the same configuration:

```sh
# recreate this project
npx sv@0.16.1 create --template minimal --types ts --install npm frontend
```

## Modes d'exécution

### Mode dev normal (backend réel) — usage standard

Requiert le backend PDS-Portail lancé sur `http://127.0.0.1:8000` (ou `PUBLIC_API_BASE_URL`).

```sh
cd frontend
npm run dev
```

Le proxy Vite redirige les appels `/api` vers le backend réel.

### Mode dev mock (local uniquement — QA sans backend)

Active des endpoints SvelteKit locaux qui servent des données de test statiques.

```sh
cd frontend
npm run dev:mock
```

Endpoints mock disponibles en mode `dev:mock` :
- `GET /api/v1/search`
- `GET /api/v1/dataset/:id`
- `GET /api/v1/resource/:id`

> **Règle absolue : ce mode est interdit en production.**
>
> - Les routes mock retournent HTTP 403 si `PUBLIC_USE_MOCK_API` n'est pas `'1'`.
> - Le build de production échoue si `PUBLIC_USE_MOCK_API=1` est présent dans l'environnement.
> - Ne jamais définir `PUBLIC_USE_MOCK_API=1` dans les variables d'environnement de déploiement.

Voir `.env.example` pour la liste complète des variables d'environnement.

## Building

> **Important : lancer les commandes depuis le dossier `frontend/`, pas la racine du repo.**

```sh
cd frontend
npm run build
```

You can preview the production build with `npm run preview`.

> To deploy your app, you may need to install an [adapter](https://svelte.dev/docs/kit/adapters) for your target environment.

## Qualification Lighthouse (PDS-34.1)

Les commandes Lighthouse standardisees utilisent deux profils reproductibles:
- `npm run lighthouse:desktop` (profil desktop avec throttling explicite)
- `npm run lighthouse:mobile` (profil mobile avec throttling explicite)
- `npm run lighthouse:all` (desktop puis mobile)
- `npm run lighthouse:suite` (demarre `preview` puis lance desktop+mobile)

### Pre-requis

1. Executer les commandes depuis `frontend/`.
2. Avoir lance un build (`npm run build`) avant `lighthouse:suite`.
3. Fournir un navigateur Chromium compatible via `LIGHTHOUSE_CHROME_PATH` si necessaire.

Exemple:

```sh
cd frontend
npm run build
LIGHTHOUSE_CHROME_PATH=/usr/bin/vivaldi npm run lighthouse:suite
```

### Parametrage des parcours cibles

Les parcours sont parametrables sans modifier le script, via variables d'environnement:

- `LIGHTHOUSE_BASE_URL`: base des URLs (defaut: `http://127.0.0.1:4173`)
- `LIGHTHOUSE_TARGET_PATHS`: liste de chemins separes par des virgules
- `LIGHTHOUSE_TARGET_URLS`: liste d'URLs absolues separees par des virgules (prioritaire)
- `LIGHTHOUSE_OUTPUT_DIR`: dossier de sortie (defaut: `./reports/lighthouse`)
- `LIGHTHOUSE_CHROME_PATH`: chemin du binaire navigateur (optionnel)
- `LIGHTHOUSE_CHROME_FLAGS`: flags Chrome (defaut: `--headless=new --no-sandbox`)

Exemple avec 3 parcours reels (recherche + filtres + variantes API):

```sh
cd frontend
LIGHTHOUSE_TARGET_PATHS='/?q=mobilite&sort=quality_desc&page=1&fmt=CSV&tag=mobilite,/?q=transport&sort=relevance&page=1&fmt=JSON&license=odc-by,/?q=energie&sort=quality_desc&page=2&fmt=CSV&organization=office-federal-de-l-energie' \
LIGHTHOUSE_CHROME_PATH=/usr/bin/vivaldi \
npm run lighthouse:all
```

### Sortie attendue

- Rapports JSON/HTML dans `frontend/reports/lighthouse/`.
- Si un seul parcours est audite:
	- `latest-desktop.report.html` + `latest-desktop.report.json`
	- `latest-mobile.report.html` + `latest-mobile.report.json`
- Si plusieurs parcours sont audites:
	- suffixes incrementaux (`latest-desktop-1`, `latest-desktop-2`, etc.).

## Qualification JS production (PDS-35)

Objectif: verifier la minification JS en build production, suivre un budget de payload JS initial et encadrer le JS inutilise.

Commande de controle:

```sh
cd frontend
LIGHTHOUSE_DESKTOP_REPORT=./reports/lighthouse/latest-desktop.report.json \
LIGHTHOUSE_MOBILE_REPORT=./reports/lighthouse/latest-mobile.report.json \
npm run validate:js-delivery
```

Le controle `validate:js-delivery` verifie:

- audit Lighthouse `unminified-javascript` a `score=1` (desktop + mobile)
- budget payload JS initial (same-origin, `resourceType=Script`)
- budget JS inutilise same-origin (`unused-javascript`)
- seuil d'alerte avant depassement (90% du budget)

Budgets initiaux retenus (MVP):

- Desktop: payload JS initial <= 50 KiB, JS inutilise same-origin <= 8 KiB
- Mobile: payload JS initial <= 50 KiB, JS inutilise same-origin <= 8 KiB

Notes de fiabilite Lighthouse:

- Les flags Chrome par defaut incluent desormais `--disable-extensions` pour reduire le bruit de scripts injectes par extensions navigateur.
- En cas d'ecart `unused-javascript` provenant de `chrome-extension://...`, traiter comme bruit environnemental et non comme charge applicative same-origin.

## Variables d'environnement

| Variable | Dev normal | Dev mock | Production |
|---|---|---|---|
| `PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` (défaut) | ignorée | URL backend cible |
| `PUBLIC_USE_MOCK_API` | absente / vide | `1` | **interdit** |

Copier `.env.example` en `.env.local` pour configurer l'environnement local.
