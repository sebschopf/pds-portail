<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import '../app.css';
	import { navigating } from '$app/state';
	import { onMount } from 'svelte';

	let { children } = $props();
	let readableMode = $state(false);

	function toggleReadableMode(): void {
		readableMode = !readableMode;
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem('pds-readable-mode', readableMode ? '1' : '0');
		}
		document.body.classList.toggle('readable', readableMode);
	}

	function focusMainContent(event: MouseEvent): void {
		event.preventDefault();
		const main = document.getElementById('main-content');
		main?.focus();
	}

	onMount(() => {
		readableMode = localStorage.getItem('pds-readable-mode') === '1';
		document.body.classList.toggle('readable', readableMode);
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>PDS Portail</title>
</svelte:head>

<div class="shell">
	<a class="skip-link" href="#main-content" onclick={focusMainContent}>Aller au contenu principal</a>

	<header>
		<p class="kicker">PDS Portail</p>
		<h1>Explorateur Open Data Suisse</h1>
		<button type="button" class="readable-toggle" onclick={toggleReadableMode}>
			{readableMode ? 'Mode lecture: actif' : 'Mode lecture: inactif'}
		</button>
	</header>

	{#if navigating.to}
		<p class="loading" role="status" aria-live="polite">Chargement en cours...</p>
	{/if}

	<main id="main-content" tabindex="-1">
		{@render children()}
	</main>
</div>

<style>
	.shell {
		max-width: var(--size-content-max);
		margin: 0 auto;
		padding: var(--space-6) var(--space-4) var(--space-7);
	}

	.skip-link {
		position: absolute;
		top: var(--space-2);
		left: var(--space-2);
		background: var(--color-primary);
		color: var(--color-on-primary);
		padding: var(--space-2) var(--space-3);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		transform: translateY(-140%);
		transition: transform 160ms ease;
		z-index: 10;
	}

	.skip-link:focus-visible {
		transform: translateY(0);
	}

	header {
		margin-bottom: var(--space-5);
	}

	.kicker {
		margin: 0;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		font-size: var(--font-size-caption);
		font-weight: 700;
		color: var(--color-primary);
	}

	h1 {
		margin: var(--space-1) 0 0;
		line-height: var(--line-height-title);
		font-family: var(--font-display);
		font-size: clamp(1.55rem, 2vw + 1rem, 2.5rem);
	}

	.loading {
		margin: 0 0 var(--space-4);
		padding: var(--space-2) var(--space-3);
		background: var(--color-surface-muted);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		display: inline-block;
		font-size: var(--font-size-ui);
	}

	.readable-toggle {
		margin-top: var(--space-3);
		border-radius: var(--radius-none);
		border: var(--border-thin) solid var(--color-border);
		background: var(--color-surface);
		color: var(--color-on-surface);
		padding: var(--space-2) var(--space-3);
		min-height: var(--size-control-md);
	}

	.readable-toggle:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	main:focus {
		outline: none;
	}

	@media (max-width: 40rem) {
		.shell {
			padding: var(--space-5) var(--space-3) var(--space-6);
		}

		h1 {
			font-size: clamp(1.35rem, 6vw, 2rem);
		}
	}
</style>
