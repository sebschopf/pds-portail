<script lang="ts">
	import { page } from '$app/state';
	import SwissCantonsMap from '$lib/assets/SwissCantonsMap.svelte';
	import '../app.css';

	const errorCode = $derived(page.status ?? 500);
	const isNotFound = $derived(page.status === 404);

	const title = $derived(
		isNotFound
			? 'Ce jeu de données s\'est égaré dans la Confédération'
			: 'Erreur serveur'
	);

	const description = $derived(
		isNotFound
			? 'La page demandée est introuvable. Explorez un canton pour lancer une recherche sur opendata.swiss.'
			: 'Une erreur inattendue est survenue. Nos équipes ont été notifiées.'
	);

	const statusLabel = $derived(
		isNotFound
			? 'Erreur 404 : page introuvable'
			: `Erreur ${errorCode} : erreur serveur`
	);
</script>

<svelte:head>
	<title>{statusLabel} — PDS Portail</title>
</svelte:head>

<div class="error-shell" role="alert" aria-live="assertive">
	<div class="error-code" aria-hidden="true">{errorCode}</div>

	<h1 class="error-title">{title}</h1>

	<p class="error-description">{description}</p>

	<div class="error-map">
		<SwissCantonsMap />
	</div>

	<nav class="error-actions" aria-label="Actions disponibles">
		<a href="/" class="error-action error-action--primary">Retour à l'accueil</a>
		<a href="/?q=" class="error-action error-action--secondary">Rechercher un jeu de données</a>
	</nav>
</div>

<style>
	.error-shell {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		padding: var(--space-12) var(--space-6);
		gap: var(--space-5);
		background: var(--color-surface-muted);
		border: var(--border-thick) solid var(--color-border);
		border-radius: var(--radius-none);
		max-width: 640px;
		margin: var(--space-10) auto;
	}

	.error-code {
		font-family: var(--font-display);
		font-size: clamp(4rem, 8vw, 8rem);
		font-weight: 800;
		line-height: var(--line-height-compact);
		color: var(--color-primary);
		margin-bottom: var(--space-2);
	}

	.error-title {
		margin: 0;
		font-size: var(--font-size-heading-lg);
		line-height: var(--line-height-title);
		color: var(--color-on-surface);
		font-weight: 700;
	}

	.error-description {
		margin: 0;
		max-width: 48ch;
		font-size: var(--font-size-body);
		line-height: var(--line-height-copy);
		color: var(--color-on-surface);
	}

	.error-map {
		margin: var(--space-6) 0;
		width: 100%;
	}

	.error-actions {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: var(--space-4);
		margin-top: var(--space-4);
	}

	.error-action {
		display: inline-block;
		padding: var(--space-3) var(--space-5);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		font-family: var(--font-body);
		font-size: var(--font-size-body);
		font-weight: 700;
		text-decoration: none;
		line-height: var(--line-height-copy);
		min-height: var(--size-control-md);
		cursor: pointer;
		transition: background-color var(--duration-fast) var(--easing-standard);
	}

	.error-action--primary {
		background: var(--color-primary);
		color: var(--color-on-primary);
	}

	.error-action--primary:hover {
		background: oklch(from var(--color-primary) calc(l - 0.06) c h);
	}

	.error-action--secondary {
		background: var(--color-surface);
		color: var(--color-on-surface);
	}

	.error-action--secondary:hover {
		background: var(--color-surface-muted);
	}

	.error-action:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	@media (max-width: 40rem) {
		.error-shell {
			padding: var(--space-8) var(--space-3);
			margin: var(--space-6) auto;
		}

		.error-actions {
			flex-direction: column;
			align-items: center;
		}

		.error-action {
			width: 100%;
			text-align: center;
		}
	}
</style>