<script lang="ts">
	import { page, navigating } from '$app/state';
	import { fade, fly } from 'svelte/transition';
	import favicon from '$lib/assets/favicon.svg';
	import { Skeleton } from '$lib';
	import '../app.css';

	let { children } = $props();
	let readableMode = $state(false);
	let initialized = $state(false);
	const routeKey = $derived(page.url.pathname);

	function toggleReadableMode(): void {
		readableMode = !readableMode;
		localStorage.setItem('pds-readable-mode', readableMode ? '1' : '0');
		document.body.classList.toggle('readable', readableMode);
	}

	function focusMainContent(event: MouseEvent): void {
		event.preventDefault();
		const main = document.getElementById('main-content');
		main?.focus();
	}

	$effect(() => {
		if (!initialized) {
			readableMode = localStorage.getItem('pds-readable-mode') === '1';
			document.body.classList.toggle('readable', readableMode);
			initialized = true;
		}
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
		<nav class="header-actions" aria-label="Navigation secondaire">
			<a href="/manuel" class="header-link">Manuel</a>
			<button type="button" class="readable-toggle" onclick={toggleReadableMode}>
				{readableMode ? 'Mode lecture: actif' : 'Mode lecture: inactif'}
			</button>
		</nav>
	</header>

	{#if navigating.to}
		<Skeleton width="100%" height="var(--border-strong)" ariaLabel="Chargement de la page" />
	{/if}

	<main id="main-content" tabindex="-1">
		{#key routeKey}
			<div class="page-transition" in:fly={{ y: 8, duration: 300 }} out:fade={{ duration: 150 }}>
				{@render children()}
			</div>
		{/key}
	</main>

	<footer class="site-footer">
		<div class="footer-content">
			<div class="footer-identity">
				<p class="footer-name">PDS Portail — Explorateur Open Data Suisse</p>
				<p class="footer-source">Données issues d’<a href="https://opendata.swiss" target="_blank" rel="noopener noreferrer">opendata.swiss</a> (CKAN, OGD Suisse)</p>
			</div>
			<nav class="footer-links" aria-label="Liens du pied de page">
				<a href="/manuel">Manuel d’utilisation</a>
			</nav>
		</div>
		<div class="footer-meta">
			<p>Conçu par <a href="https://schopfer.moustik.site" target="_blank" rel="noopener noreferrer">Sébastien Schopfer</a></p>
			<p>Accessibilité WCAG 2.2 AA · Conforme RGPD</p>
		</div>
	</footer>
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

	.header-actions {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		margin-top: var(--space-3);
	}

	.header-link {
		font-size: var(--font-size-ui);
		font-weight: 650;
		color: var(--color-primary);
		text-decoration-thickness: 2px;
		padding: var(--space-2) var(--space-3);
		min-height: var(--size-control-md);
		display: inline-flex;
		align-items: center;
	}

	.header-link:hover {
		color: var(--color-on-surface);
	}

	.header-link:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	/* ── Footer ─────────────────────────────── */

	.site-footer {
		margin-top: var(--space-7);
		padding-top: var(--space-4);
		border-top: var(--border-thin) solid var(--color-border);
		text-align: center;
	}

	.footer-content {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		align-items: baseline;
		gap: var(--space-4);
		margin-bottom: var(--space-3);
	}

	.footer-identity {
		text-align: left;
	}

	.footer-name {
		margin: 0;
		font-size: var(--font-size-ui);
		font-weight: 700;
		color: var(--color-on-surface);
	}

	.footer-source {
		margin: 0;
		font-size: var(--font-size-caption);
		color: var(--color-on-surface-subtle);
	}

	.footer-links {
		display: flex;
		gap: var(--space-3);
	}

	.footer-links a {
		font-size: var(--font-size-ui);
		font-weight: 650;
		color: var(--color-primary);
		text-decoration-thickness: 2px;
	}

	.footer-links a:hover {
		color: var(--color-on-surface);
	}

	.footer-meta {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: var(--space-3);
	}

	.footer-meta p {
		margin: 0;
		font-size: var(--font-size-caption);
		color: var(--color-on-surface-subtle);
	}

	.site-footer a {
		font-weight: 650;
		text-decoration-thickness: 2px;
	}

	.site-footer a:hover {
		color: var(--color-primary);
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
