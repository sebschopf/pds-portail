# Règles Frontend SvelteKit — PDS-Portail

> Appliquées à `frontend/src/**/*.{svelte,ts,js}`

---

## Design System (SPEC-003/004/006) — CRITIQUE

**Toutes les valeurs CSS DOIVENT utiliser les tokens du design system. Aucune valeur hardcodée autorisée.**

### Tokens obligatoires

| Catégorie | Token | Exemple |
|-----------|-------|---------|
| **Couleurs** | `var(--color-*)` (OKLCH uniquement) | `var(--color-primary)`, `var(--color-error)`, `var(--color-success)` |
| **Espacement** | `var(--space-1)` à `var(--space-7)` (4px→48px) | `var(--space-3)` jamais `16px` |
| **Bordures** | `var(--border-thin)` (1px) ou `var(--border-strong)` (2px) | Jamais `1px solid #fff` |
| **Animation** | Durée: `var(--duration-fast\|normal\|slow)` + Easing: `var(--easing-standard\|emphasized\|decelerated)` | — |
| **Border-radius** | MVP : `var(--radius-none)` **UNIQUEMENT** (SPEC-003 §3.4 "aucun arrondi autorisé") | Ni `--radius-small` ni `--radius-medium` |
| **Font-size** | `clamp(min, preferred, max)` responsive | `clamp(0.875rem, 1rem, 1.125rem)` |

### Validation design

```bash
npm run validate:design   # OKLCH + contraste AA
```

- Lighthouse a11y doit être 100/100 desktop ET mobile.
- Toujours auditer le CSS après toute modification de composant.

## Accessibilité (WCAG 2.2 AA — Non Négociable)

| Règle | Exigence |
|-------|----------|
| **Labels** | Tout champ de formulaire a un `<label>` associé OU `aria-label`. Pas de placeholder seul. |
| **Erreurs** | Messages d'erreur avec `role="alert"` |
| **Clavier** | Tout élément interactif est focusable au clavier, ordre logique, pas de piège clavier |
| **Contraste** | ≥ 4.5:1 texte normal (AA), ≥ 7:1 cible (AAA). Auto-vérifié par `validate:design` |
| **ARIA** | Labels explicites sur composants interactifs, rôles sémantiques, `aria-label` sur icônes seules |
| **Skip-link** | Lien d'évitement présent, premier élément focusable |
| **Langue** | `lang="fr"` sur `<html>`, titres de page uniques et descriptifs |

## Typographie

- Police : Atkinson Hyperlegible (locale, pas de CDN)
- Body : min 18px, line-height 1.6
- Pas de serif sauf contenu éditorial long
- OKLCH uniquement (pas de hex, rgb, hsl)

## Architecture (ADR-020)

- SvelteKit 5 avec SSR
- Pages : `+page.svelte` + `+page.ts` (load functions pour données)
- Composants dans `lib/ui/` (Atomic Design)
- Types dans `lib/types/`, contrats runtime dans `lib/contracts/`
- Pas de CDN externe (privacy by design, RGPD — ADR-014)

## Sécurité

- CSP déclarative dans `svelte.config.ts` (`kit.csp.mode: 'nonce'`)
- Rate-limiting côté backend (slowapi 30 req/min)
- `PUBLIC_USE_MOCK_API !== '1'` en production — jamais de mock en prod

## Performance & Lighthouse (SPEC-005) — CRITIQUE

Les seuils Lighthouse CI sont bloquants. Tout commit qui dégrade les scores est rejeté.

### Seuils minimum (desktop + mobile)

| Métrique | Desktop | Mobile |
|----------|---------|--------|
| **Performance** | ≥ 95 | ≥ 90 |
| **Accessibilité** | 100 | 100 |
| **Best Practices** | ≥ 95 | ≥ 90 |
| **SEO** | ≥ 95 | ≥ 90 |

### Commandes

```bash
# Suite complète desktop + mobile (avant tout commit)
npm run lighthouse:suite

# Vérification des seuils dans le rapport le plus récent
npm run check:lighthouse

# Profil individuel
npm run lighthouse:desktop
npm run lighthouse:mobile
```

### Règles

- Exécuter `npm run lighthouse:suite` avant chaque commit frontend.
- Si un seuil est sous la limite : corriger avant de commettre, pas d'exception.
- Les rapports sont stockés dans `frontend/reports/lighthouse/` (datés + `latest-*`).
- JS budget : pas plus de 150KB gzippé par page (vérifié par `npm run validate:js-delivery`).

## Tests

```bash
npx svelte-check          # 0 erreur
npm run test              # vitest : tous les tests passent
npm run build             # build Vercel sans erreur
npm run validate:design   # tokens OKLCH + contraste AA
npm run lighthouse:suite  # seuils desktop + mobile
```

- Tests orientés comportement, pas assertions fragiles sur le markup.
- Tests UI : vérifications ARIA et navigation clavier incluses.

## Références

- SPEC-003: Design system contract (couleurs, spacing, motion, radius)
- SPEC-004: UI implementation guide (Atomic Design, responsive)
- SPEC-005: Performance Frontend et Assurance Qualité (Lighthouse seuils)
- SPEC-006: Component reference
- ADR-020: Frontend architecture (SvelteKit, SSR, load functions)
- ADR-014: Assets locaux, pas de CDN externe