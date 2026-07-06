# SPEC-009 : Service payant — Surveillance des changements d'etat

## Identification

| Propriete | Valeur |
|-----------|--------|
| **Titre** | Service payant — Surveillance des changements d'etat |
| **Version** | 0.4 |
| **Date** | 2026-07-06 |
| **Auteur** | mous_tik |
| **Statut** | En revision |
| **Phase du projet** | M11 - Monétisation & Exploration Premium |

---

## 1. Resume executif

### Probleme

Un utilisateur qui a identifie un dataset pertinent n'a aujourd'hui aucun moyen simple d'etre prevenu lorsqu'il change. Il doit revenir manuellement sur le portail pour verifier les mises a jour, les ressources ajoutees ou supprimees, ou une degradation de qualite.

### Solution proposee

Un service de surveillance permet a un abonne d'associer son email a un ou plusieurs datasets, puis de recevoir des alertes email lorsque des changements sont detectes dans le cycle d'ingestion.

### Objectif primaire

Un abonne reçoit un email lorsqu'un dataset surveille change, puis peut consulter la liste de ses surveillances et l'historique associe sans compte utilisateur classique.

### Portee documentaire

Cette SPEC documente le **service effectivement livre et observable dans le code** a date.

Elle ne sert pas a figer des evolutions techniques non encore stabilisees. Les sujets de convergence ou d'ecart sont deplaces vers :
- ADR-028 : choix du prestataire Polar
- ADR-029 : envoi des emails transactionnels
- ADR-030 : identite email et acces watcher
- ADR-033 : securite et idempotence des webhooks
- ADR-034 : cible d'integration Polar proposee
- SPEC-012 : convergence paiement Polar et acces watchers

---

## 2. Perimetre fonctionnel actuel

### 2.1 Abonnement initial

1. L'utilisateur consulte une fiche dataset.
2. Il ouvre la modale "Surveiller ce dataset".
3. Il saisit son email.
4. Le frontend le redirige vers Polar Checkout avec le produit configure et le contexte dataset.
5. A reception du webhook Polar de creation de commande, PDS-Portail cree ou retrouve un watcher, puis associe le dataset.
6. Un email de bienvenue peut etre envoye apres creation de la surveillance.

### 2.2 Consultation des surveillances

1. L'utilisateur accede a `/alertes` avec un `token` watcher dans l'URL, ou via un token deja present en `localStorage`.
2. Le frontend charge les surveillances via `GET /api/v1/watchers?token=...`.
3. Le frontend charge l'historique via `GET /api/v1/alerts?token=...`.

### 2.3 Gestion des surveillances

1. L'utilisateur peut supprimer une surveillance dataset par dataset.
2. Une annulation d'abonnement Polar suspend le watcher existant.

---

## 3. Contrats locaux actuellement exposes

### 3.1 Frontend dataset

Le composant `WatchDataset.svelte` :
- lit un identifiant produit Polar depuis une variable publique ;
- construit une URL checkout Polar cote frontend ;
- transmet l'email et le contexte dataset dans cette redirection ;
- stocke un token watcher par dataset en `localStorage` lorsqu'il est disponible.

### 3.2 Backend paiement et watchers

Les contrats actuellement exposes sont :

```text
POST /api/v1/webhooks/polar
POST /api/v1/watchers
GET /api/v1/watchers?token=...
DELETE /api/v1/watchers/{watched_dataset_id}?token=...
GET /api/v1/alerts?token=...
```

Comportement actuellement observe :
- le webhook Polar traite `order.created` pour creer la surveillance ;
- le webhook Polar traite `subscription.cancelled` pour suspendre un watcher ;
- `POST /api/v1/watchers` existe comme creation/fallback manuel ;
- `/alerts` et `/watchers` reposent sur un token UUID permanent de watcher.

### 3.3 Contrats non livres a ce jour

Les elements suivants ne doivent pas etre consideres comme service livre dans cette SPEC :
- `POST /api/v1/polar/checkout-sessions`
- activation metier sur `order.paid`
- flux utilisateur `/alertes?magic=...`
- endpoint public `POST /api/v1/magic-link`
- endpoints internes de supervision documentes mais non exposes dans le code courant

Ces sujets sont traites comme cible de convergence dans SPEC-012 et ADR-034.

---

## 4. Modele de donnees utile au service

Le service repose aujourd'hui principalement sur :
- `watchers`
- `watched_datasets`
- `change_log`

Une table `magic_links` existe deja dans la persistence, mais son flux utilisateur n'est pas considere comme livre de bout en bout dans le perimetre courant.

---

## 5. Invariants fonctionnels actuels

- L'email est l'identite primaire du watcher.
- Aucun compte utilisateur classique n'est requis.
- Les donnees bancaires ne transitent pas ni ne sont stockees par PDS-Portail.
- Un token watcher permanent permet l'acces a `/alertes` et a la gestion des surveillances.
- Une surveillance est associee a un dataset via le backend, pas directement confiee au navigateur comme source de verite.
- Les changements detectes sont historises avant consultation utilisateur.

---

## 6. Exigences techniques tracables

- [SPEC-F13 | PRD-F14 | M11] Detecter les changements d'etat des datasets surveilles a chaque cycle d'ingestion.
- [SPEC-F14 | PRD-F14 | M11] Notifier les abonnes par email apres detection d'un changement.
- [SPEC-F15 | PRD-F16 | M11] Permettre la gestion des surveillances existantes.
- [SPEC-F16 | PRD-F15 | M11] Integrer un paiement mensuel pour le service de surveillance.
- [SPEC-F17 | PRD-F14 | M11] Stocker et suivre l'historique des changements par dataset.

---

## 7. Non-scope de cette SPEC

Les sujets suivants sont volontairement exclus du perimetre normatif de SPEC-009, soit parce qu'ils ne sont pas stabilises, soit parce qu'ils relevent d'une cible future :

- choix definitif Checkout Link vs Checkout Session backend
- mapping webhook cible complet (`order.paid`, `subscription.active`, `subscription.past_due`, `subscription.revoked`)
- generalisation du flux magic link utilisateur
- endpoints internes de supervision et statistiques d'exploitation
- plan annuel, multi-produit ou tarification evoluee

Ils sont documentes ou a converger dans SPEC-012 et ADR-034.

---

## 8. References

- ADR-028 : choix du prestataire Polar
- ADR-029 : envoi des emails transactionnels
- ADR-030 : identite email, magic links et token permanent
- ADR-033 : securite des webhooks
- ADR-034 : cible d'integration Polar
- SPEC-012 : convergence paiement Polar et acces watchers
