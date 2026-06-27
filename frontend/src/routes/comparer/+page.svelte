<script lang="ts">
	import { Button, EmptyState } from '$lib';
	import type { CompareItem } from '$lib/types/compare';

	let { data }: { data: { error: string | null; items: CompareItem[] } } = $props();

	const items = $derived(data?.items ?? []);
	const error = $derived(data?.error ?? null);

	/**
	 * Rend une pastille coloree selon le score (OKLCH semantique).
	 * Vert >=70, orange 40-69, rouge <40, gris si absent.
	 */
	function qualityClass(score: number | null): string {
		if (score === null) return 'metric-unknown';
		if (score >= 70) return 'metric-good';
		if (score >= 40) return 'metric-warn';
		return 'metric-bad';
	}

	function freshnessClass(days: number | null): string {
		if (days === null) return 'metric-unknown';
		if (days <= 30) return 'metric-good';
		if (days <= 180) return 'metric-warn';
		return 'metric-bad';
	}

	function metricLabel(value: number | null, suffix: string = ''): string {
		return value === null ? 'Non renseigné' : `${value}${suffix}`;
	}

	/** Formats pour affichage (liste triée, fallback si vide). */
	function formatsLabel(formats: string[]): string {
		return formats.length > 0 ? formats.sort().join(', ') : 'Non renseignés';
	}

	function tagsLabel(tags: string[]): string {
		return tags.length > 0 ? tags.slice(0, 6).join(', ') : 'Aucun tag';
	}
</script>

<svelte:head>
	<title>Comparaison de datasets - PDS Portail</title>
</svelte:head>

<section class="compare-page">
	<h1>Comparaison de datasets</h1>

	<nav class="back-nav">
		<a href="/" class="back-link" aria-label="Retour aux résultats de recherche">
			← Retour aux résultats
		</a>
	</nav>

	{#if error}
		<EmptyState
			variant="error"
			title="La comparaison a échoué"
			description="Réessayez ou réduisez le nombre de jeux de données sélectionnés. {error}"
		>
			{#snippet action()}
				<a href="/" class="back-link">Retour à la recherche</a>
			{/snippet}
		</EmptyState>
	{:else if items.length < 2}
		<EmptyState
			title="Aucun jeu de données à comparer"
			description="Sélectionnez au moins 2 jeux de données depuis les résultats de recherche."
		>
			{#snippet action()}
				<a href="/" class="back-link">Retour à la recherche</a>
			{/snippet}
		</EmptyState>
	{:else}
		<!-- Desktop : tableau HTML semantique -->
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<div class="table-wrapper" role="region" aria-label="Tableau comparatif — défiler horizontalement si nécessaire" tabindex="0">
			<table class="compare-table" aria-label="Tableau comparatif de datasets">
				<caption class="sr-only">
					Comparaison de {items.length} datasets sur 9 critères. Les colonnes
					représentent les datasets, les lignes les critères de comparaison.
				</caption>
				<thead>
					<tr>
						<th scope="col" class="compare-label-col">Critère</th>
						{#each items as item (item.id)}
							<th scope="col" class="compare-col">
								<a href="/dataset/{encodeURIComponent(item.id)}">{item.title}</a>
							</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					<tr>
						<th scope="row" class="compare-label-col">Organisation</th>
						{#each items as item (item.id)}
							<td class="compare-col">{item.org_name ?? 'Non renseignée'}</td>
						{/each}
					</tr>
					<tr>
						<th scope="row" class="compare-label-col">Licence</th>
						{#each items as item (item.id)}
							<td class="compare-col">{item.license ?? 'Non renseignée'}</td>
						{/each}
					</tr>
					<tr>
						<th scope="row" class="compare-label-col">Score qualité</th>
						{#each items as item (item.id)}
							<td class="compare-col">
								<span class="metric-badge {qualityClass(item.quality_score)}">
									{metricLabel(item.quality_score, '/100')}
								</span>
							</td>
						{/each}
					</tr>
					<tr>
						<th scope="row" class="compare-label-col">Complétude</th>
						{#each items as item (item.id)}
							<td class="compare-col">
								<span class="metric-badge {qualityClass(item.completeness)}">
									{metricLabel(item.completeness, '%')}
								</span>
							</td>
						{/each}
					</tr>
					<tr>
						<th scope="row" class="compare-label-col">Fraîcheur</th>
						{#each items as item (item.id)}
							<td class="compare-col">
								<span class="metric-badge {freshnessClass(item.freshness_days)}">
									{item.freshness_days === null
										? 'Non renseigné'
										: `${item.freshness_days} jours`}
								</span>
							</td>
						{/each}
					</tr>
					<tr>
						<th scope="row" class="compare-label-col">Formats</th>
						{#each items as item (item.id)}
							<td class="compare-col">{formatsLabel(item.resource_formats)}</td>
						{/each}
					</tr>
					<tr>
						<th scope="row" class="compare-label-col">Nb ressources</th>
						{#each items as item (item.id)}
							<td class="compare-col">{item.resource_count}</td>
						{/each}
					</tr>
					<tr>
						<th scope="row" class="compare-label-col">Tags</th>
						{#each items as item (item.id)}
							<td class="compare-col">{tagsLabel(item.tags)}</td>
						{/each}
					</tr>
					<tr>
						<th scope="row" class="compare-label-col">Description</th>
						{#each items as item (item.id)}
							<td class="compare-col desc-col">
								{item.description ?? 'Aucune description.'}
							</td>
						{/each}
					</tr>
				</tbody>
			</table>
		</div>

		<!-- Mobile : cartes empilees -->
		<div class="compare-mobile" aria-label="Comparaison datasets (vue mobile)">
			{#each items as item (item.id)}
				<article class="compare-card" aria-labelledby={`compare-title-${item.id}`}>
					<h3 id={`compare-title-${item.id}`}>
						<a href="/dataset/{encodeURIComponent(item.id)}">{item.title}</a>
					</h3>
					<dl>
						<dt>Organisation</dt>
						<dd>{item.org_name ?? 'Non renseignée'}</dd>
						<dt>Licence</dt>
						<dd>{item.license ?? 'Non renseignée'}</dd>
						<dt>Score qualité</dt>
						<dd>
							<span class="metric-badge {qualityClass(item.quality_score)}">
								{metricLabel(item.quality_score, '/100')}
							</span>
						</dd>
						<dt>Complétude</dt>
						<dd>
							<span class="metric-badge {qualityClass(item.completeness)}">
								{metricLabel(item.completeness, '%')}
							</span>
						</dd>
						<dt>Fraîcheur</dt>
						<dd>
							<span class="metric-badge {freshnessClass(item.freshness_days)}">
								{item.freshness_days === null
									? 'Non renseigné'
									: `${item.freshness_days} jours`}
							</span>
						</dd>
						<dt>Formats</dt>
						<dd>{formatsLabel(item.resource_formats)}</dd>
						<dt>Nb ressources</dt>
						<dd>{item.resource_count}</dd>
						<dt>Tags</dt>
						<dd>{tagsLabel(item.tags)}</dd>
						<dt>Description</dt>
						<dd>{item.description ?? 'Aucune description.'}</dd>
					</dl>
				</article>
			{/each}
		</div>
	{/if}
</section>

<style>
	.compare-page {
		display: grid;
		gap: var(--space-4);
		max-width: 100%;
	}

	h1 {
		margin: 0;
		font-size: var(--font-size-heading-2xl);
	}

	.back-nav {
		margin: 0;
	}

	.back-link {
		font-weight: 600;
		color: var(--color-primary);
	}

	/* --- Tableau desktop --- */
	.table-wrapper {
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
		border: var(--border-thin) solid var(--color-border);
	}

	.table-wrapper:focus-visible {
		outline: var(--border-thin) solid var(--color-primary);
		outline-offset: var(--outline-offset);
	}

	.compare-table {
		width: 100%;
		border-collapse: collapse;
	}

	.compare-label-col {
		padding: var(--space-2) var(--space-3);
		font-weight: 700;
		font-size: var(--font-size-ui);
		background: var(--color-surface-muted);
		border-bottom: var(--border-thin) solid var(--color-border);
	}

	.compare-col {
		padding: var(--space-2) var(--space-3);
		border-bottom: var(--border-thin) solid var(--color-border);
		font-size: var(--font-size-ui);
		overflow-wrap: anywhere;
	}

	.desc-col {
		max-height: 8rem;
		overflow-y: auto;
	}

	.compare-col a {
		font-weight: 700;
		color: var(--color-primary);
	}

	thead .compare-col {
		background: var(--color-surface-muted);
		font-weight: 700;
	}

	/* Badges metriques */
	.metric-badge {
		display: inline-block;
		padding: var(--space-0) var(--space-2);
		font-weight: 700;
		font-size: var(--font-size-ui);
		border: var(--border-thin) solid transparent;
	}

	.metric-good {
		background: var(--color-success);
		color: var(--color-on-success);
		border-color: var(--color-success);
	}

	.metric-warn {
		background: var(--color-warning);
		color: var(--color-on-warning);
		border-color: var(--color-warning);
	}

	.metric-bad {
		background: var(--color-danger);
		color: var(--color-on-danger);
		border-color: var(--color-danger);
	}

	.metric-unknown {
		background: var(--color-surface-muted);
		color: var(--color-on-surface-subtle);
		border-color: var(--color-border);
	}

	/* --- Vue mobile : cartes empilees --- */
	.compare-mobile {
		display: none;
	}

	@media (max-width: 43.75rem) {
		.compare-table {
			display: none;
		}

		.compare-mobile {
			display: grid;
			gap: var(--space-3);
		}

		.compare-card {
			padding: var(--space-4);
			border: var(--border-thin) solid var(--color-border);
			background: var(--color-surface);
		}

		.compare-card h3 {
			margin: 0 0 var(--space-2);
			font-size: var(--font-size-heading-lg);
		}

		.compare-card dl {
			display: grid;
			gap: var(--space-1);
			margin: 0;
		}

		.compare-card dt {
			font-weight: 700;
			font-size: var(--font-size-ui);
			color: var(--color-on-surface-muted);
		}

		.compare-card dd {
			margin: 0 0 var(--space-2);
			font-size: var(--font-size-ui);
		}
	}
</style>