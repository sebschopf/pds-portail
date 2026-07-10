# Roadmap — PDS-Portail Explorateur Open Data Suisse

## Identification

| Propriété           | Valeur                                                |
|---------------------|-------------------------------------------------------|
| **Titre**           | Roadmap PDS-Portail                                   |
| **Version**         | 2.1                                                   |
| **Date**            | 2026-07-06                                            |
| **Auteur**          | mous_tik + Cline                                      |
| **Statut**          | En cours (M10 en clôture, M11 actif)                  |
| **Phase du projet** | Post-MVP — Préparation multisource                    |

---

## 0. Contexte global : pourquoi cette roadmap change

### Ce qui s'est passé

PDS-Portail a été conçu pour ingérer exclusivement l'API CKAN d'opendata.swiss. Le MVP a été livré, 9 milestones (M1-M9) ont été complétés entre avril et juin 2026. Le produit est stable, déployé, couvert à 88% de tests backend et 90 tests frontend.

### L'événement déclencheur

La Confédération suisse a décidé d'abandonner CKAN comme plateforme opendata.swiss. La raison exacte n'est pas publique, mais le plan est clair :

1. **I14Y** (plateforme d'interopérabilité suisse, `api.i14y.admin.ch`) est le répertoire centralisé des métadonnées de la Confédération : datasets, APIs gouvernementales, concepts sémantiques, prestations publiques. Son API publique v1 existe déjà.
2. **metadata.swiss** sera la plateforme qui fusionnera opendata.swiss (CKAN) et I14Y. Horizon annoncé : **2028**.

### Ce qu'on a fait face à ça

Le 28 juin 2026, on a mené une exploration technique complète de l'API I14Y (PDS-72, documentée dans [SPEC-008](../../20-technique/01-spec/spec-008-exploration-i14y.md)). Résultat :

- L'API fonctionne, les données sont plus riches que CKAN (multilingue structuré, vocabulaire contrôlé)
- **Mais** les IDs CKAN et I14Y sont incompatibles (pas de jointure), les structures de données ne sont pas disponibles sur tous les datasets, et le filtre keyword est cassé
- **Décision** ([ADR-026](../../30-decisions/adr/0026-report-integration-i14y.md)) : on n'intègre pas I14Y tout de suite. On prépare le terrain et on surveille.

### La stratégie

| Horizon | Action | Pourquoi |
|---------|--------|----------|
| **M10 (maintenant)** | Préparer le schéma, documenter la veille, analyser les gaps | Pour ne pas être pris au dépourvu quand CKAN s'arrêtera |
| **2026-2027** | Surveiller I14Y et metadata.swiss, améliorer l'UX | Le produit continue de tourner sur CKAN, on l'améliore |
| **2028** | Migrer vers l'API unifiée metadata.swiss | CKAN sera remplacé, on bascule sur la nouvelle plateforme |

### Ce qui ne change pas

L'architecture (FastAPI + SQLite + SvelteKit 5), les engagements accessibilité (WCAG AA/AAA), la confidentialité (RGPD, no-CDN), et la mission : rendre les données publiques suisses accessibles à tous.

---

## 1. Rétrospective : ce qui a été livré (M1-M9)

### M1-M5 : MVP (avril-juin 2026)

| Milestone | Contenu clé | Statut |
|-----------|-------------|--------|
| M1 | Fondations backend : FastAPI, SQLAlchemy, SQLite, ingestion CKAN | ✅ |
| M2 | Frontend recherche : SvelteKit 5, barre de recherche, filtres facettés | ✅ |
| M3 | Détail dataset : fiche complète, QualityBlock, structure lisible | ✅ |
| M4 | Accès ressources : vue ressource, parcours search→detail→access | ✅ |
| M5 | Déploiement : Vercel (FE), Render/Fly.io (BE), CI/CD Tangled | ✅ |

### M6 : Recherche différenciante (juin 2026)

- PDS-40 : Ranking hybride explicable (texte 50%, qualité 30%, fraîcheur 20%)
- PDS-41 : Recherche multilingue FR/DE/IT/EN avec expansion de requête
- PDS-42 : Affichage "Pourquoi ce résultat" dans les cartes de recherche
- PDS-43 : Comparaison guidée de datasets (2 à 4, tableau comparatif)

### M7 : Robustesse opérationnelle (juin 2026)

- PDS-44 : Index FTS5 et facettes pré-calculées
- PDS-45 : Métriques d'ingestion CKAN
- PDS-46 : Cache multi-niveaux avec invalidation fine (TTL 24h, hit/miss/ratio)
- PDS-47 : Instrumentation KPI Time-to-first-relevant-dataset
- PDS-49 : Validation persistance cache
- PDS-52 : Ingestion CKAN incrémentale avec offset persistant
- PDS-53 : Synchro CKAN différentielle (réduction ~100 → ~1-3 requêtes/cycle)

### M8 : Durcissement sécurité (juin 2026)

- PDS-38 : Headers de sécurité web (HSTS, CSP, X-Frame-Options, COOP, etc.)
- PDS-54 : Rate-limiting API publique (slowapi, 30 req/min)
- PDS-55 : Dockerfile multi-stage, utilisateur non-root
- PDS-56 : CSP stricte (no inline scripts, connect-src restreint)
- PDS-57 : Typage SvelteKit complet (App.PageData, App.Error, etc.)
- PDS-58 : Métriques d'usage via cache (top queries, zero results)
- PDS-59 : Baseline Lighthouse dans `make quality` (desktop ≥90, mobile ≥70)

### M9 : Polish Frontend (juin 2026)

- PDS-60 : Skeletons et états de chargement (shimmer OKLCH)
- PDS-61 : États vides illustrés (EmptyState réutilisable)
- PDS-62 : Page 404 personnalisée (carte des 26 cantons)
- PDS-63 : Transitions et micro-interactions (fade, fly, slide)
- PDS-64 : Nettoyage fondations UI (bits-ui retiré, ~50KB économisés)
- PDS-65 : Réorganisation Atomic Design (atoms/molecules/organisms)
- PDS-66 : Tokens de motion et contrat d'animation
- PDS-67 : Librairie d'icônes SVG néo-brutalistes (6 icônes)
- PDS-68 : Documentation Design System (SPEC-006, guides icônes, checklist accessibilité)
- PDS-69 : Polish cosmétique (icônes intégrées, espacements, overflow, footer)
- PDS-70 : Timeout recherche 3+ termes, FTS5 unicode61, recherche instantanée
- PDS-71 : Accents français + colonne `source` schéma cache

---

## 2. En cours : M10 — Préparation multisource (juin 2026)

**Objectif** : Préparer PDS-Portail à la transition CKAN → metadata.swiss sans casser l'existant.

### Tâches

| ID | Tâche | Statut | Livrable |
|----|-------|--------|----------|
| PDS-71 | Ajouter colonne `source` au schéma cache | ✅ Done | `source` VARCHAR, DEFAULT 'ckan' sur organizations, datasets, resources |
| PDS-72 | Protocole de veille I14Y/metadata.swiss | ✅ Done | [veille-i14y-metadata-swiss.md](../../20-technique/07-veille/veille-i14y-metadata-swiss.md) |
| PDS-74 | Mise à jour roadmap post-MVP (ce document) | ✅ Done | Ce document |
| PDS-75 | Gap analysis schéma cache vs DCAT-AP Suisse | ○ To Do | Document d'analyse d'écart |
| PDS-73 | Schéma de cache orienté source (normalisateur) | ○ To Do | Refactor du normalisateur pour supporter source= paramétrable |

### Pourquoi ces tâches

- **PDS-71** : La colonne `source` permet de coexister CKAN et I14Y dans les mêmes tables quand le jour viendra. Sans ça, il faudrait une migration lourde.
- **PDS-72** : On ne peut pas intégrer I14Y maintenant, mais on doit savoir **quand** le faire. Le protocole de veille définit 8 signaux de bascule et une fréquence bimensuelle.
- **PDS-74** : La roadmap doit refléter la nouvelle réalité pour qu'en juillet on ne soit pas perdu.
- **PDS-75** : DCAT-AP CH est le standard que metadata.swiss utilisera probablement. Comparer notre schéma actuel au standard permet d'anticiper les migrations.
- **PDS-73** : Aujourd'hui le normalisateur est codé en dur pour CKAN. Le rendre paramétrable prépare l'arrivée d'une deuxième source.

### Signaux de bascule (voir ADR-026 et PDS-72)

Si l'un de ces signaux apparaît, on réévalue immédiatement :

| Signal | Statut actuel |
|--------|---------------|
| Un champ `ckanId` ou `opendataSwissId` apparaît dans l'API I14Y | ❌ Absent |
| L'endpoint structures I14Y devient systématiquement disponible | ❌ 404 |
| L'API unifiée metadata.swiss est disponible en bêta | ❌ Pas encore |
| Un besoin utilisateur concret émerge pour les données I14Y | ❌ Aucun |

---

## 3. Court terme : M11 — Convergence service payant + améliorations UX (juillet 2026)

**Objectif** : Stabiliser le service payant de surveillance, fermer les écarts entre documentation et implémentation, puis reprendre les améliorations UX sur une base cohérente.

### Tâches actives et prochaines

| ID | Tâche | Statut | Livrable |
|----|-------|--------|----------|
| PDS-114 | Finaliser la décision checkout/webhooks Polar | ✅ Done | Décision V1 documentée dans ADR-034 + SPEC-012 stabilisée |
| PDS-116 | Converger le backend watchers/webhooks | ✅ Done | Backend et tests alignés sur le flux retenu |
| PDS-115 | Converger le frontend surveillance et accès alertes | ✅ Done | Frontend aligné sur le contrat V1 retenu |
| PDS-117.1 | Implémenter le flux magic link bout en bout pour l'accès /alertes | ✅ Done | Consommation publique `?magic=`, bascule token local et tests e2e du parcours email |
| PDS-117 | Convergence V1 surveillance datasets | ✅ Done | Initiative parent, impact mesuré, convergence clôturée |
| PDS-76 | Page publique « Suite du projet » | ✅ Done | Route `/suite` expliquant la transition opendata.swiss → metadata.swiss |

### Axes M11

| Axe | Pourquoi maintenant | Priorité |
|-----|---------------------|----------|
| Convergence service payant | Le service existe mais mélange V1 livrée, briques préparatoires et cible documentaire | Haute |
| Transparence produit | La page `/suite` explique la transition metadata.swiss et réduit l'incertitude côté utilisateur | Haute |
| Qualité d'accès aux alertes | Le flux `/alertes` doit être cohérent avec l'identité email et les contrats backend | Haute |
| Améliorations recherche | À reprendre une fois la convergence du service payant terminée | Moyenne |
| Dark mode / onboarding | Toujours optionnels, mais non prioritaires tant que la convergence n'est pas close | Basse |

### Règle de pilotage M11

Tant que PDS-114, PDS-115, PDS-116 et PDS-117 ne sont pas clos, la priorité M11 n'est pas d'ajouter de nouvelles capacités au service payant, mais de rendre son comportement auditable, cohérent et exploitable de bout en bout.

État de suivi au 2026-07-06 :
- la décision V1 checkout/webhooks est stabilisée (✅ PDS-114) ;
- les convergences backend et frontend V1 sont livrées (✅ PDS-116, PDS-115) ;
- l'écart structurant restant avant clôture de PDS-117 est le parcours magic link de bout en bout (`✅ PDS-117.1`).
- **PDS-117 et PDS-117.1 sont clôturés** : M11 converge vers sa clôture.

### Travaux optionnels post-M11 (M12)

Les tâches suivantes sont des nettoyages/refactors post-PDS-117.1, assignés à M12 (priorité moyenne à basse) :
- **PDS-105** : Backend Tests — Éliminer les reload modules et stabiliser les fixtures d'intégration ✅
- **PDS-106** : Backend Tests — Couvrir `invalidate_cache_after_sync` et adapters critiques (9 tests, 366 lignes, couverture 91.41%) ✅
- **PDS-118** : Refactor magic link tests pour clocks contrôlables (déterminisme) ✅
- **PDS-119** : Clarifier stratégie error messages magic link (UX vs sécurité, ADR-031)
- **PDS-120** : Refactor router.py — déplacer imports au niveau module (maintenabilité 1085 lignes) ✅

### Exécution opérationnelle Polar (M14)

Une fois la convergence M11 livrée, le jumeau opérationnel doit être exécuté en production pour valider le flux de bout en bout :

| ID | Tâche | Statut | Livrable |
|----|-------|--------|----------|
| PDS-121 | Mise en conformité Polar Checkout et Webhooks (cadrage) | ○ To Do | Checklist, critères d'acceptation, dépendance vers PDS-121.1 |
| PDS-121.1 | Exécution opérationnelle Polar (prod, signatures, E2E, preuves Go/No-Go) | ○ To Do | Preuves archivées, checklist Go/No-Go complétée, rapport E2E |

Ces tâches ne modifient pas le code : elles vérifient, valident et documentent l'état de la production.

---

## 4. Moyen terme : 2027 — Veille et sandbox

**Objectif** : Maintenir le produit, surveiller l'écosystème, expérimenter sans engager.

### Actions

1. **Veille continue** : appliquer le protocole PDS-72 (vérification bimensuelle des 8 signaux)
2. **Sandbox DCAT** : si l'API metadata.swiss est disponible en bêta, créer un environnement de test pour valider l'ingestion
3. **Exploration I14Y open-source** : quand I14Y passe en open-source (fin 2026), étudier le code pour anticiper les schémas
4. **Mises à jour de dépendances** : maintenir FastAPI, SvelteKit, SQLAlchemy à jour
5. **Améliorations continues** : itérer sur le feedback utilisateur

### Ne pas faire en 2027

- Intégrer I14Y comme source secondaire tant qu'aucun signal de bascule n'est détecté (ADR-026)
- Migrer vers une nouvelle base de données (SQLite suffit pour le volume actuel)
- Ajouter des comptes utilisateurs (hors périmètre PRD)

---

## 5. Long terme : 2028 — Migration metadata.swiss

**Objectif** : Basculer de l'API CKAN opendata.swiss vers l'API unifiée metadata.swiss.

### Scénario probable

1. metadata.swiss unifie CKAN + I14Y dans une API unique (standard DCAT-AP CH probable)
2. L'API CKAN opendata.swiss est dépréciée ou coupée
3. PDS-Portail migre son ingestion vers la nouvelle API

### Préparation déjà faite

| Préparation | Statut |
|-------------|--------|
| Colonne `source` dans le cache | ✅ PDS-71 |
| Protocole de veille | ✅ PDS-72 |
| Roadmap documentée | ✅ PDS-74 (ce document) |
| Gap analysis DCAT-AP CH | ⬜ PDS-75 |
| Normalisateur paramétrable | ⬜ PDS-73 |

### Inconnues (à clarifier d'ici 2028)

- L'API metadata.swiss sera-t-elle compatible DCAT-AP CH ?
- Les IDs CKAN seront-ils préservés ou traduits ?
- Y aura-t-il une période de coexistence CKAN + metadata.swiss ?
- Le volume de données sera-t-il significativement différent ?

---

## 6. Timeline visuelle

```
2026 Q2 (avr-juin)  ████████████████████  M1-M9 : MVP + Recherche + Robustesse + Sécurité + Polish
2026 Q3 (juil-sept)  ████                  M10 : Préparation multisource (en cours)
2026 Q3 (juil-sept)  ████                  M11 : Convergence service payant + améliorations UX
2026 Q4 (oct-déc)    ░░░░                  Veille I14Y + sandbox si bêta
2027                 ░░░░░░░░░░░░░░░░░░░░  Veille continue, maintenance, itérations UX
2028                 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  Migration metadata.swiss

████ = Développement actif
░░░░ = Veille et maintenance
▓▓▓▓ = Migration
```

---

## 7. Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|-----------|
| metadata.swiss retarde au-delà de 2028 | Moyenne | Faible | CKAN opendata.swiss devrait rester opérationnel ; notre ingestion continue de fonctionner |
| L'API metadata.swiss est radicalement différente de CKAN et I14Y | Moyenne | Élevé | La colonne `source` + le normalisateur paramétrable (PDS-73) réduisent le coût de migration |
| CKAN est coupé avant que metadata.swiss soit prêt | Faible | Élevé | Le protocole de veille (PDS-72) surveille les annonces ; on aurait le temps de réagir |
| Un concurrent intègre I14Y avant nous | Faible | Faible | Pas de concurrence identifiée ; la valeur du portail est dans l'UX et les indicateurs qualité, pas dans l'exclusivité des données |
| Fatigue du solo dev | Moyenne | Élevé | ADR-driven decisions, documentation systématique, protocole de veille pour ne pas avoir à "suivre" activement |

---

## 8. Références

| Document | Lien |
|----------|------|
| Discovery Brief | [discovery-brief.md](../01-cadrage/discovery-brief.md) |
| PRD | [prd.md](../02-prd/prd.md) |
| SPEC-001 Architecture | [spec-001-technical-architecture.md](../../20-technique/01-spec/spec-001-technical-architecture.md) |
| SPEC-008 Exploration I14Y | [spec-008-exploration-i14y.md](../../20-technique/01-spec/spec-008-exploration-i14y.md) |
| SPEC-009 Service livré surveillance | [spec-009-service-payant-surveillance-changements.md](../../20-technique/01-spec/spec-009-service-payant-surveillance-changements.md) |
| SPEC-012 Convergence surveillance | [spec-012-convergence-paiement-polar-et-acces-watchers.md](../../20-technique/01-spec/spec-012-convergence-paiement-polar-et-acces-watchers.md) |
| ADR-026 Report I14Y | [0026-report-integration-i14y.md](../../30-decisions/adr/0026-report-integration-i14y.md) |
| Protocole de veille | [veille-i14y-metadata-swiss.md](../../20-technique/07-veille/veille-i14y-metadata-swiss.md) |
| Tous les ADR | [30-decisions/adr/](../../30-decisions/adr/) |
| Backlog | `backlog/tasks/` (géré via Backlog.md) |

---

**Document propriétaire — PDS-Portail | Version 2.1 | Créé 2026-06-13, mis à jour 2026-07-06 (PDS-74)**