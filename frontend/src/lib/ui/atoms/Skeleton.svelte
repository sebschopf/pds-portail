<script lang="ts">
	/**
	 * Squelette shimmer réutilisable — indique un contenu en chargement.
	 *
	 * Animation : gradient OKLCH qui glisse horizontalement.
	 * Accessibilité : respecte prefers-reduced-motion (durée 0ms, pas d'animation).
	 *
	 * Tokens utilisés :
	 *   --duration-slow (500ms) pour l'animation shimmer, défini dans motion.css
	 *   --easing-standard (ease) pour la courbe de l'animation
	 *   Ces tokens proviennent de SPEC-003 §3.7 "Motion et Animations".
	 *   En prefers-reduced-motion: reduce, motion.css force toutes les durées
	 *   à 0ms, ce qui stoppe le shimmer. Ce comportement est exigé par ADR-005
	 *   (WCAG 2.2 §2.3.3 — Animation from Interactions).
	 *
	 * @see Doc/20-technique/01-spec/spec-003-frontend-design-system-contract.md §3.7
	 * @see Doc/30-decisions/adr/adr-005-accessibility.md
	 */
	let {
		width = '100%',
		height = '1.2em',
		variant = 'block',
		ariaLabel = 'Chargement en cours'
	}: {
		width?: string;
		height?: string;
		variant?: 'block' | 'text' | 'circle';
		ariaLabel?: string;
	} = $props();
</script>

<div
	class="skeleton skeleton-{variant}"
	style="width: {width}; height: {height};"
	role="status"
	aria-live="polite"
	aria-label={ariaLabel}
>
	<span class="sr-only">Chargement...</span>
</div>

<style>
	.skeleton {
		display: block;
		background: var(--color-surface-muted);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		position: relative;
		overflow: hidden;
		/* Pas d'animation par défaut, gérée par l'état global prefers-reduced-motion */
	}

	.skeleton::after {
		content: '';
		position: absolute;
		inset: 0;
		background: linear-gradient(
			90deg,
			transparent 0%,
			oklch(0.995 0.004 95 / 0.6) 40%,
			oklch(0.995 0.004 95 / 0.6) 60%,
			transparent 100%
		);
		transform: translateX(-100%);
		animation: shimmer var(--duration-slow) var(--easing-standard) infinite;
	}

	.skeleton-circle {
		border-radius: var(--radius-none);
	}

	.skeleton-text {
		border: none;
		background: var(--color-surface-muted);
		border-radius: var(--radius-none);
	}

	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}

	@keyframes shimmer {
		100% {
			transform: translateX(100%);
		}
	}
</style>