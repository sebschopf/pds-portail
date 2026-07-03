# ADR-030 : Magic Links a usage unique pour l'acces a /alertes

## Statut

Accepted

## Date

2026-06-29

## Contexte

Le service de surveillance des changements (SPEC-009) necessite un mecanisme d'acces pour que l'abonne puisse consulter ses datasets surveilles et l'historique des changements (page `/alertes`). La page doit etre accessible sans login/mot de passe classique (ADR-005), et le lien doit etre cliquable depuis un email.

**Principe fondamental : l'email EST l'identité.** L'abonné n'a pas de compte, pas de mot de passe, pas de login. Son email, saisi au moment du paiement, est son seul identifiant. Prouver qu'on possède l'email = prouver qu'on est l'abonné.

Le modèle économique est un abonnement Polar (ADR-028).

## Decision Drivers

1. **Pas d'authentification classique** : pas de login, pas de mot de passe, pas de sessions (ADR-005).
2. **L'email est l'identité** : l'email saisi au paiement est le seul identifiant du watcher. Pas de compte utilisateur.
3. **Lien cliquable depuis un email** : compatible avec les clients email standard.
4. **Pas de token permanent dans les URLs d'email** : un email transféré ne doit pas donner un accès permanent à `/alertes`.
5. **Accès récurrent sans friction** : l'abonné doit pouvoir consulter `/alertes` le lendemain sans redemander un email, et sans repayer.

Le contrat de lecture associé à ce flux doit rester explicite côté backend: le use case de détection des changements lit le dataset courant via un port exposant `get_dataset(dataset_id)`. Tout nouvel adapter raccordé à cette chaîne doit implémenter ce contrat pour éviter une divergence silencieuse entre cache et détection.

## Flux d'authentification

1. **Paiement** : L'utilisateur saisit son email (ex: `jean@example.com`) dans la modale "Surveiller". PDS-Portail envoie cet email à Polar avec le paiement. Polar le transmet dans le webhook. PDS-Portail crée un watcher lié à `jean@example.com`. L'email saisi au paiement, l'email de bienvenue, et l'email d'alerte sont **le même email**.

2. **Email d'alerte** : Un changement est detecte. PDS-Portail genere un magic link (token temporaire, 15 min, usage unique) lie au watcher, et l'envoie a `jean@example.com`. Le lien dirige vers `/alertes?magic={token}`.

3. **Clic sur le lien** : Le backend verifie le magic link (hash SHA-256, lookup `magic_links`, expiration, usage). Le magic link est lie au watcher (via `magic_links.watcher_id`), pas a l'email directement. Le watcher a un abonnement actif -> l'utilisateur est authentifie. Le backend marque `used_at` a la premiere utilisation et refuse toute reutilisation du meme magic link. Le frontend recoit le token permanent et le stocke en `localStorage`.

4. **Le lendemain** : L'utilisateur va sur `/alertes`. Le `localStorage` contient le token permanent → accès direct. Ni email, ni paiement nécessaire.

5. **Changement de navigateur** : L'utilisateur saisit `jean@example.com` sur la page `/alertes`. Un watcher avec abonnement actif existe pour cet email -> un nouveau magic link gratuit est envoye. L'abonnement Polar est deja actif, il ne repaie pas.

## Options considérées

### Option 1 : Token UUID v4 permanent dans l'URL d'email — rejetée

Un email transféré donnerait un accès permanent.

### Option 2 : Token hashé avec sel — rejetée

Aucun avantage si l'email est intercepté.

### Option 3 : JWT signé — rejetée

Toujours permanent dans l'URL. Même problème.

### Option 4 : URLs signees HMAC (48h) — rejetee

Fenetre de 48h si email transfere. Probleme attenue mais pas resolu.

### Option 5 : Magic Links (15 minutes, usage unique) — acceptee

Token temporaire (UUID v4, hashe SHA-256) dans une table `magic_links`. Le token est valide 15 minutes maximum et ne peut etre utilise qu'une seule fois. Le token permanent (`watchers.token`) n'est jamais dans les URLs d'email, il sert uniquement au `localStorage`.

## Décision

**Magic Links (Option 5).** Double mecanisme : magic link temporaire (emails) + token permanent (localStorage). L'email est l'identite, le magic link est le moyen d'en prouver la possession.

### Table `magic_links`

```sql
CREATE TABLE magic_links (
    id TEXT PRIMARY KEY,           -- UUID v4
    token_hash TEXT NOT NULL,      -- SHA-256 du token temporaire
    watcher_id TEXT NOT NULL REFERENCES watchers(id),
    created_at TEXT NOT NULL,      -- ISO 8601
    expires_at TEXT NOT NULL,      -- created_at + 15 minutes
    used_at TEXT                   -- NULL tant que non utilise
);
```

### Endpoints

- `GET /api/v1/alertes?magic={token}` : vérifie le magic link, renvoie le token permanent + données
- `GET /api/v1/alertes?token={watcher_token}` : fallback localStorage
- `POST /api/v1/magic-link` : body `{email}` → cherche un watcher actif pour cet email → génère et envoie un magic link

Regles de verification du magic link :
- `expires_at > now()`
- `used_at IS NULL`
- apres succes, `used_at` est renseigne dans la meme transaction

## Conséquences

### Positives
- Email transfere = au maximum 1 acces valide pendant 15 minutes
- L'email est l'identité, pas de compte à créer
- localStorage maintient l'accès sans friction
- L'abonné ne repaie jamais pour se ré-authentifier

### Négatives
- Une table `magic_links` supplémentaire
- Latence email (~1-5 secondes) pour le premier accès
- Si localStorage vidé, l'utilisateur doit redemander un magic link
- Un lien deja utilise devient immediatement invalide

### Actions requises
- Créer la table `magic_links`
- Adapter `SendAlertsUseCase` pour générer des magic links
- Créer `POST /api/v1/magic-link`
- Formulaire email sur `/alertes` (fallback si pas de localStorage)
- Tests pytest

## Liens

- SPEC : [SPEC-009](../../20-technique/01-spec/spec-009-service-payant-surveillance-changements.md)
- ADR-027 : clé API exploration (mécanisme distinct)
- ADR-028 : paiement Polar
- ADR-029 : envoi d'emails
- ADR-005 : pas de cookies, pas de sessions

### Documentation de référence

- [OWASP : Forgot Password Cheat Sheet (magic links)](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)
- [hashlib SHA-256 Python stdlib](https://docs.python.org/3/library/hashlib.html)
- [uuid Python stdlib (génération UUID v4)](https://docs.python.org/3/library/uuid.html)