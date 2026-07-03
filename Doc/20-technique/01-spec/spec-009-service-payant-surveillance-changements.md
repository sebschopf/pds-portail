# SPEC-009 : Service payant — Surveillance des changements d'état

## Identification

| Propriété           | Valeur                                                |
|---------------------|-------------------------------------------------------|
| **Titre**           | Service payant — Surveillance des changements d'état |
| **Version**         | 0.1                                                   |
| **Date**            | 2026-06-28                                            |
| **Auteur**          | mous_tik                                              |
| **Statut**          | Brouillon                                             |
| **Phase du projet** | M11 - Monétisation & Exploration Premium              |

---

## 1. Résumé exécutif

### Problème

Un utilisateur qui a identifié un dataset pertinent n'a aucun moyen de savoir si ce dataset est mis à jour, modifié, ou si sa qualité se dégrade. Il doit revenir manuellement sur le portail pour vérifier. Pour un journaliste qui suit un sujet ou un analyste qui base un rapport sur ces données, cette absence de notification est un risque.

### Solution proposée

Un service d'abonnement mensuel (~5 CHF/mois) qui permet à l'utilisateur de surveiller des datasets. À chaque cycle d'ingestion CKAN, le backend compare l'état actuel des datasets surveillés avec leur état précédent. Si un changement est détecté (mise à jour, nouvelle ressource, lien cassé, dégradation de qualité), une alerte email est envoyée aux abonnés concernés.

### Objectif primaire

Un abonné reçoit un email dans les 24h suivant un changement détecté sur un dataset qu'il surveille, sans avoir à revenir consulter le portail.

---

## 2. Parcours utilisateur

### Phase 1 : Abonnement

1. L'utilisateur (gratuit) consulte une fiche dataset. Il voit un bouton "Surveiller ce dataset".
2. Il clique. Une modale s'ouvre : "Surveillez les changements de ce dataset. 5 CHF/mois. Vous recevrez un email à chaque mise à jour."
3. Il saisit son email et procède au paiement. Il est redirigé vers Polar Checkout avec son email et l'ID du dataset passés en paramètres.
4. Paiement confirmé. Polar appelle le webhook `order.created` sur PDS-Portail, qui crée le watcher (email, polar_subscription_id, token permanent interne) et l'association watcher-dataset.
5. PDS-Portail envoie un **email de bienvenue** : "Vous surveillez {dataset_title}. Vous recevrez une alerte à chaque changement." Cet email contient un **lien d'accès** à `/alertes` (magic link temporaire, 15 minutes).

**Comment l'email est lié au paiement** : l'utilisateur saisit son email dans PDS-Portail avant d'être redirigé vers Polar. Cet email est passé en paramètre à Polar (`customer_email`). Polar le transmet dans le webhook `order.created`. PDS-Portail ne stocke jamais de données bancaires.

### Phase 2 : Alerte de changement

6. Au prochain cycle d'ingestion, si le dataset surveillé est modifié, PDS-Portail envoie un **email d'alerte**.
7. L'email contient :
   - Nom du dataset
   - Nature du changement (mise à jour, ressource ajoutée/supprimée, lien cassé, qualité dégradée)
   - Score de qualité actuel
  - **Lien "Voir les changements"** -> `/alertes?magic={token_temporaire}` (15 minutes, usage unique)

### Phase 3 : Consultation des changements

8. L'utilisateur clique sur le lien dans l'email.
9. Le lien a **deux fonctions** :
   - **Authentifier** l'utilisateur sans mot de passe (le magic link prouve qu'il possède l'email)
   - **Le diriger vers la page `/alertes`** qui affiche l'historique complet des changements pour tous ses datasets surveillés
10. Au premier clic valide, le frontend recoit et stocke le **token permanent** en `localStorage`.
11. Le backend marque le magic link comme consomme (`used_at`), toute reutilisation du meme lien est refusee.

**Le lendemain, comment revoir les changements sans le lien ?**

12. L'utilisateur retourne sur `/alertes` (favori, historique du navigateur, ou il tape l'URL). Le `localStorage` contient le token permanent -> acces direct, **pas besoin de l'email, pas de nouveau paiement**.
13. Si l'utilisateur change de navigateur, utilise la navigation privee, ou vide son `localStorage` : la page `/alertes` affiche un formulaire "Entrez votre email pour voir vos surveillances". Il saisit son email -> recoit un **nouveau magic link gratuit** (15 minutes) -> retrouve l'acces. **Il ne repaie pas**, l'abonnement Polar est deja actif.

### Phase 4 : Gestion et renouvellement

12. Depuis `/alertes`, l'utilisateur peut voir l'historique des changements, arrêter une surveillance, ou se désabonner.
13. Le renouvellement est mensuel via Polar. Si le paiement échoue, les alertes sont suspendues (pas supprimées). L'utilisateur peut réactiver.

---

## 3. Solution technique

### 3.1 Backend

#### Tables

```sql
CREATE TABLE watchers (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    polar_subscription_id TEXT,
    plan TEXT NOT NULL DEFAULT 'monthly',
    status TEXT NOT NULL DEFAULT 'active',  -- active, suspended, cancelled
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE watched_datasets (
    id TEXT PRIMARY KEY,
    watcher_id TEXT NOT NULL REFERENCES watchers(id),
    dataset_id TEXT NOT NULL,
    last_known_metadata_modified TEXT,
    last_known_resource_count INTEGER,
    last_known_quality_score REAL,
    created_at TEXT NOT NULL,
    UNIQUE(watcher_id, dataset_id)
);

CREATE TABLE change_log (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    change_type TEXT NOT NULL,  -- metadata_updated, resource_added, resource_removed, quality_degraded, link_broken
    previous_value TEXT,
    new_value TEXT,
    detected_at TEXT NOT NULL,
    notified_at TEXT
);
```

#### Détection des changements

Intégrée dans `SyncCkanBatchUseCase` ou dans un use case dédié `DetectChangesUseCase` exécuté après chaque cycle d'ingestion :

1. Pour chaque dataset dans `watched_datasets` :
   - Comparer `metadata_modified` avec `last_known_metadata_modified`.
   - Comparer le nombre de ressources avec `last_known_resource_count`.
   - Recalculer le score de qualité et comparer avec `last_known_quality_score`.
   - Vérifier l'intégrité des URLs de ressources (HEAD request).
  - Le port de lecture utilisé par `DetectChangesUseCase` doit exposer un accès à `get_dataset(dataset_id)`; tout nouvel adapter de lecture branché sur cette détection doit respecter ce contrat.
2. Si un changement est détecté, insérer une entrée dans `change_log`.
3. Mettre à jour les valeurs `last_known_*` dans `watched_datasets`.

#### Envoi des alertes

Un use case `SendAlertsUseCase` exécuté périodiquement (après chaque détection) :

1. Requêter `change_log` où `notified_at IS NULL`.
2. Grouper par `dataset_id`.
3. Pour chaque dataset modifié, trouver les `watchers` actifs associés.
4. Envoyer un email à chaque watcher.
5. Marquer `notified_at` dans `change_log`.

**Template d'email** :
```
Sujet : [PDS-Portail] Changement détecté : {dataset_title}

Bonjour,

Le dataset "{dataset_title}" que vous surveillez a été modifié :

- Dernière mise à jour : {new_modified_date}
- Changement détecté : {change_description}
- Qualité actuelle : {quality_score}/100

Consultez la fiche : https://pds-portail.vercel.app/dataset/{dataset_id}

Voir mes alertes : https://pds-portail.vercel.app/alertes?magic={magic_link_token}
```

#### Envoi d'emails

- Utiliser `smtplib` (stdlib Python) avec un compte SMTP (ex: Infomaniak, Mailgun free tier).
- Template HTML + texte brut.
- Rate limiting : max 1 email par watcher par dataset par 24h (même si changements multiples).
- Lien de désabonnement dans chaque email.

### 3.2 Frontend

#### Page dataset : bouton "Surveiller"

- Bouton "Surveiller ce dataset" sur la fiche dataset.
- Au clic, modale avec :
  - Explication du service (2 CHF/mois, alertes email).
  - Champ email.
  - Bouton de paiement (redirection Polar Checkout).
- Après paiement, confirmation et badge "Surveillé" sur la fiche.

#### Page `/alertes`

- Accessible via lien tokenisé dans les emails.
- Liste des datasets surveillés.
- Bouton "Arrêter la surveillance" par dataset.
- Bouton "Historique des changements" par dataset.
- Lien de désabonnement global.

#### Composant `WatchDataset.svelte`

**États** :
- `idle` : bouton "Surveiller".
- `modal` : formulaire email + paiement.
- `pending` : attente confirmation paiement.
- `active` : badge "Surveillé" + lien "Gérer".
- `error` : message d'erreur.

### 3.3 Paiement

- **Prestataire** : Polar, Merchant of Record (MoR), open-source, developer-first. ADR-028.
- **Pourquoi un MoR** : TVA, facturation et comptabilité gérées automatiquement. Zéro charge administrative.
- **CHF natif** : prix affiché et facturé en CHF (130+ devises supportées). Facteur décisif pour un produit suisse.
- **Plan mensuel** : 5 CHF/mois (Starter gratuit, 5% + 0.50$ de commission).
- **Webhook `order.created`** : active le watcher et associe le dataset surveillé.
- **Webhook `subscription.cancelled`** : suspend l'abonnement (statut `'suspended'`).
- **Fallback manuel V1** : lien de paiement Polar hébergé + endpoint `POST /api/v1/watchers` pour activation manuelle.
- **Variables d'environnement** : `POLAR_API_KEY`, `POLAR_WEBHOOK_SECRET`, `POLAR_ORGANIZATION_ID`.

---

## 4. Sécurité

- Tokens d'accès à la page `/alertes` : UUID unique par watcher, pas d'auth classique.
- Emails jamais exposés publiquement.
- Polar gère les données de paiement en tant que Merchant of Record (pas de stockage côté PDS-Portail).
- Rate limiting sur l'envoi d'emails : max 50/jour (limites SMTP gratuites).

---

## 5. Exigences techniques traçables

- [SPEC-F13 | PRD-F14 | M11] Détecter les changements d'état des datasets surveillés à chaque cycle d'ingestion.
- [SPEC-F14 | PRD-F14 | M11] Notifier les abonnés par email dans les 24h suivant un changement.
- [SPEC-F15 | PRD-F16 | M11] Permettre la gestion des surveillances (ajout, suppression, historique).
- [SPEC-F16 | PRD-F15 | M11] Intégrer un paiement mensuel (5 CHF/mois) pour le service de surveillance.
- [SPEC-F17 | PRD-F14 | M11] Stocker et suivre l'historique des changements par dataset.

---

## 6. Tarification proposée

| Plan | Prix | Surveillances | Alertes |
|---|---|---|---|
| Mensuel | 5 CHF/mois | 10 datasets max | Email à chaque changement |
| Annuel | 50 CHF/an | 10 datasets max | Email à chaque changement |

---

## 7. Endpoints internes de supervision

Tous les endpoints internes sont protégés par `INTERNAL_API_TOKEN` (header `Authorization: Bearer <token>`).

### 7.1 Statistiques des watchers

```
GET /api/v1/internal/watchers/stats
```

**Réponse (200)** :
```json
{
  "total_watchers": 15,
  "active": 12,
  "suspended": 3,
  "watched_datasets": 28
}
```

### 7.2 Statistiques des alertes

```
GET /api/v1/internal/alerts/stats
```

**Réponse (200)** :
```json
{
  "changes_detected": 156,
  "notified": 148,
  "pending_notification": 8,
  "last_email_sent_at": "2026-06-29T12:00:00Z",
  "smtp_errors_last_24h": 0
}
```

### 7.3 Statut SMTP

```
GET /api/v1/internal/alerts/smtp-status
```

**Réponse (200)** :
```json
{
  "connected": true,
  "last_error_at": null,
  "last_error_message": null,
  "consecutive_errors": 0
}
```

### 7.4 Statistiques des webhooks Polar

```
GET /api/v1/internal/webhooks/polar/stats
```

**Réponse (200)** :
```json
{
  "last_received_at": "2026-06-29T11:00:00Z",
  "total_received": 23,
  "last_error_at": null,
  "signature_errors": 0
}
```

### 7.5 Statistiques des magic links

```
GET /api/v1/internal/magic-links/stats
```

**Réponse (200)** :
```json
{
  "total_issued": 89,
  "used": 72,
  "expired_unused": 15,
  "expired_count": 15
}
```

### 7.6 Nettoyage des magic links expirés

```
POST /api/v1/internal/magic-links/cleanup
```

Supprime tous les magic links où `expires_at < now() - 24h`. Retourne le nombre de liens supprimés.

```json
{
  "deleted": 15
}
```

### 7.7 Suspendre un watcher manuellement

```
PATCH /api/v1/internal/watchers/{watcher_id}
Body: {"status": "suspended"}
```

Passe le statut du watcher à `suspended` (les emails d'alerte cessent, l'abonnement Polar n'est pas affecté).

---

## 8. Non-scope

- Alertes SMS ou push.
- Surveillance de datasets hors opendata.swiss.
- Alertes sur des critères personnalisés (seuil de qualité, mot-clé).
- Tableau de bord multi-utilisateurs.

---

## 9. Références

### Décisions d'architecture (ADR)

- [ADR-028 : Paiement Polar](../../../Doc/30-decisions/adr/0028-paiement-polar-surveillance.md)
- [ADR-029 : Envoi d'emails](../../../Doc/30-decisions/adr/0029-envoi-emails-surveillance.md)
- [ADR-030 : Magic Links / token watcher](../../../Doc/30-decisions/adr/0030-token-watcher-surveillance.md)

### Documentation officielle Polar

- [Introduction & Vue d'ensemble](https://polar.sh/docs/introduction)
- [API Overview (auth, base URLs, rate limits)](https://polar.sh/docs/api-reference/introduction)
- [Checkout Links (lien simple, approche recommandée frontend)](https://polar.sh/docs/features/checkout/links)
- [Checkout Session API (création dynamique backend)](https://polar.sh/docs/features/checkout/session)
- [Webhooks : setup et configuration](https://polar.sh/docs/integrate/webhooks/endpoints)
- [Webhooks : liste des événements](https://polar.sh/docs/integrate/webhooks/events)
- [Webhooks : validation signature et livraison](https://polar.sh/docs/integrate/webhooks/delivery)
- [Webhook `order.created` (activation abonnement)](https://polar.sh/docs/api-reference/webhooks/order.created)
- [Webhook `order.paid` (paiement confirmé)](https://polar.sh/docs/api-reference/webhooks/order.paid)
- [Webhook `subscription.canceled` (suspension)](https://polar.sh/docs/api-reference/webhooks/subscription.canceled)
- [Subscriptions : cycle de vie](https://polar.sh/docs/features/subscriptions/introduction)
- [Customer State (vérifier un abonnement actif)](https://polar.sh/docs/integrate/customer-state)
- [SDK Python (polar-sdk)](https://polar.sh/docs/integrate/sdk/python)
- [Adapter SvelteKit](https://polar.sh/docs/integrate/sdk/adapters/sveltekit)
- [Merchant of Record : frais transparents](https://polar.sh/docs/merchant-of-record/fees)
- [Sandbox (tests sans carte réelle)](https://polar.sh/docs/integrate/sandbox)
- [Code source GitHub (Apache 2.0)](https://github.com/polarsource/polar)
- [Référence LLM complète](https://polar.sh/docs/llms-full.txt)

### Python stdlib

- [smtplib — SMTP protocol client](https://docs.python.org/3/library/smtplib.html)
- [hashlib — SHA-256](https://docs.python.org/3/library/hashlib.html)
- [uuid — UUID v4](https://docs.python.org/3/library/uuid.html)
