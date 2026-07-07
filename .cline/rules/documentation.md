# Règles Documentation — PDS-Portail

> Appliquées à `**/*.md`

---

## CHANGELOG — Règles strictes

**Format** : [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/) + [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Sections obligatoires

```markdown
## [Unreleased]

### Added       — nouvelles fonctionnalités
### Changed     — modifications de fonctionnalités existantes
### Fixed       — corrections de bugs
```

> Pas de sections `Removed`, `Security`, `Deprecated` sauf réel besoin.

### Format des entrées

```markdown
- PDS-XXX: [Type] description courte — contexte complet avec liens specs/ADRs si complexité accrue
```

### Règles de rédaction

1. **Préfixe PDS-XX obligatoire** sur chaque entrée (même multi-tickets).
2. **Verbe d'action en français** : "ajout de…", "correction du…", "refactor de…".
3. **Description concise** (1-2 lignes) mais avec contexte suffisant pour comprendre l'impact.
4. **Liens specs/ADR** quand la complexité le justifie (ex: `conformité SPEC-003/004`, `ADR-030`).
5. **Une ligne par ticket**, sauf si plusieurs sous-tickets livrés ensemble → regroupement autorisé (ex: PDS-82/83).
6. **Pas de détails d'implémentation** dans le changelog (noms de classes, fichiers) — rester fonctionnel.
7. **Commits = messages en français préfixés** aussi, mais le changelog est la source de vérité narrative.

### Exemples

```markdown
### Added
- PDS-117.1: flux magic link bout en bout — endpoints `/magic-link/consume` et `/magic-link` (anti-énumération), 
  validation hash/expiration/usage-unique/watcher-actif, intégration frontend `/alertes?magic=...`, 
  templates email HTML/TXT, 7 tests backend + 113 tests frontend, conformité SPEC-003/004/006, ADR-030.

### Changed
- PDS-88: envoi d'alertes email durci avec rate-limit strict par couple watcher+dataset sur 24h.

### Fixed
- PDS-119: consommation de magic link durcie contre l'énumération par message d'erreur unifié.
```

### Versioning

- **Unreleased** : tout ce qui n'est pas encore tagué.
- **X.Y.Z** : tag de release (semver). Incrémenter **MINOR** pour nouvelles features, **PATCH** pour bugfixes.
- Date de release en ISO 8601 (`YYYY-MM-DD`).

---

## Index des SPEC de référence

### Architecture cœur
- **SPEC-001**: Architecture technique (hexagonale, couches, contrats API)
- **SPEC-003**: Contrat design system (couleurs, tokens, format OKLCH, accessibilité)
- **SPEC-004**: Implémentation UI (Atomic Design, responsive, spacing, typographie)

### Qualité & Tests
- **SPEC-005**: Performance Frontend et Assurance Qualité (Lighthouse seuils, JS budgets, validation)
- **SPEC-011**: Fiabilisation suite tests backend (test harness stable, déterminisme, anti-flaky, couverture)

### Fonctionnalités
- **SPEC-009**: Service de surveillance (changelog, types de changements, alertes, templates email)
- **SPEC-012**: Intégration paiement Polar (checkout, webhooks, cycle de vie watcher, convergence)

### Décisions (ADR)
- **ADR-020**: Architecture frontend (SvelteKit, SSR, load functions, stores)
- **ADR-029**: Envoi d'emails (SMTP, templates, Brevo, gestion d'erreurs)
- **ADR-030**: Tokens magic link (temporaires, hash SHA-256, usage unique, validité 15min)
- **ADR-034**: Checkout Polar (frontend-hosted, webhook mapping minimal)

---

## Règles de synchronisation documentaire

1. **Si endpoint/schema change** → Mettre à jour SPEC-009/012 si comportement utilisateur affecté
2. **Si design change** → Mettre à jour SPEC-003/004 si tokens ou patterns changent
3. **Si architecture change** → Nouvel ADR si structurel/long-terme
4. **Si patterns test/qualité changent** → Mettre à jour règles backend/frontend
5. **Jamais committer** les fichiers sous `backlog/` (signaler qu'ils sont internes)

---

## Champs de tâche Backlog

**Toujours mettre à jour :**
- `status` : Draft → To Do → In Progress → Blocked → Done
- `modifiedFiles` : Liste exacte des fichiers modifiés (chemins relatifs racine)
- `finalSummary` : Accomplissement, nombre de tests, specs/ADR, risques résiduels

**Optionnel :**
- `acceptanceCriteria` : Critères numérotés et testables
- `dependencies` : Tâches préalables
- `milestone` : Phase active de la roadmap

---

## Source of Truth — Résolution de conflits

Quand roadmap, SPEC, ADR, et backlog sont en désaccord :
1. **Expliciter le désaccord** (ne pas choisir silencieusement une source).
2. **Résoudre** : la roadmap prime pour le séquencement, les SPEC/ADR priment pour l'implémentation.
3. **Documenter la résolution** dans le ticket ou le CHANGELOG.