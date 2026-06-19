<script lang="ts">
	import { appendSearchContext } from '$lib/navigation/search-context';

	type DatasetCardItem = {
		id: string;
		title: string;
		org_name: string | null;
		description: string | null;
		quality_score: number | null;
		completeness: number | null;
		freshness_days: number | null;
		resource_formats: string[];
		resource_count: number;
		tags: string[];
	};

	let {
		dataset,
		searchContext = null
	}: {
		dataset: DatasetCardItem;
		searchContext?: string | null;
	} = $props();

	const MAX_TAGS = 5;

	function metricOrUnknown(value: number | null): string {
		return value === null ? 'Non renseigne' : `${value}`;
	}

	const visibleTags = $derived(dataset.tags.slice(0, MAX_TAGS));
	const hasMoreTags = $derived(dataset.tags.length > MAX_TAGS);
	const safeFormats = $derived(dataset.resource_formats.length > 0 ? dataset.resource_formats : ['Non renseigne']);
	const datasetLink = $derived(
		appendSearchContext(`/dataset/${encodeURIComponent(dataset.id)}`, searchContext)
	);
	const datasetApiLink = $derived(`/api/v1/dataset/${encodeURIComponent(dataset.id)}`);
</script>

<article class="dataset-card" aria-labelledby={`dataset-title-${dataset.id}`}>
	<header class="dataset-head">
		<h3 id={`dataset-title-${dataset.id}`}>{dataset.title}</h3>
		<p class="meta">Organisation: {dataset.org_name ?? 'Non renseignee'}</p>
	</header>

	<p>{dataset.description ?? 'Description non disponible.'}</p>

	<dl class="metrics" aria-label="Indicateurs dataset">
		<div>
			<dt>Qualite</dt>
			<dd>{metricOrUnknown(dataset.quality_score)}</dd>
		</div>
		<div>
			<dt>Completude</dt>
			<dd>{metricOrUnknown(dataset.completeness)}</dd>
		</div>
		<div>
			<dt>Fraicheur (jours)</dt>
			<dd>{metricOrUnknown(dataset.freshness_days)}</dd>
		</div>
		<div>
			<dt>Ressources</dt>
			<dd>{dataset.resource_count}</dd>
		</div>
	</dl>

	<p class="meta"><strong>Formats:</strong> {safeFormats.join(', ')}</p>
	<p class="meta">
		<strong>Tags:</strong>
		{#if dataset.tags.length === 0}
			Non renseignes
		{:else}
			{visibleTags.join(', ')}{hasMoreTags ? ', ' : ''}{#if hasMoreTags}<span aria-hidden="true">...</span><span class="sr-only">et d autres tags</span>{/if}
		{/if}
	</p>

	<p class="links">
		<a href={datasetLink} aria-label={`Ouvrir la fiche: ${dataset.title}`}>
			Ouvrir la fiche dataset
		</a>
	</p>

	<p class="links">
		<a href={datasetApiLink} target="_blank" rel="noopener noreferrer">
			Voir le detail API dataset
			<span class="sr-only">(nouvelle fenetre)</span>
		</a>
	</p>
</article>

<style>
	.dataset-card {
		display: grid;
		gap: var(--space-3);
		background: var(--color-surface);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		padding: var(--space-4);
	}

	.dataset-head {
		display: grid;
		gap: var(--space-1);
	}

	h3 {
		margin: 0;
		font-size: var(--font-size-heading-xl);
		line-height: var(--line-height-relaxed);
		overflow-wrap: anywhere;
	}

	p {
		margin: 0;
	}

	.meta {
		font-size: var(--font-size-ui);
		color: var(--color-on-surface-subtle);
	}

	.metrics {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
		gap: var(--space-2);
		margin: 0;
	}

	dt {
		font-size: var(--font-size-ui);
		color: var(--color-on-surface-muted);
	}

	dd {
		margin: var(--space-1) 0 0;
		font-weight: 700;
	}

	.links a {
		font-weight: 600;
		text-decoration-thickness: 2px;
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
</style>
