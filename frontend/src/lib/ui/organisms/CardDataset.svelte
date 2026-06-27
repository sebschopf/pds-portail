<script lang="ts">
	import { appendSearchContext } from '$lib/navigation/search-context';
	import type { RankingSignals } from '$lib/types/ranking';
	import type { SearchDatasetItem } from '$lib/types/search';

	let {
		dataset,
		searchContext = null,
		isCompared = false,
		compareDisabled = false,
		onToggleCompare = () => {}
	}: {
		dataset: SearchDatasetItem;
		searchContext?: string | null;
		isCompared?: boolean;
		compareDisabled?: boolean;
		onToggleCompare?: (id: string) => void;
	} = $props();

	const MAX_TAGS = 5;

	function metricOrUnknown(value: number | null): string {
		return value === null ? 'Non renseigne' : `${value}`;
	}

	function percentLabel(value: number): string {
		return `${Math.round(value * 100)}%`;
	}

	/**
	 * Traduit les signaux bruts du ranking hybride en raisons lisibles,
	 * triees par contribution decroissante. Chaque raison est ponderee
	 * (ex: text_score * weight_text) pour refleter son poids reel dans le score.
	 * Les composantes nulles sont omises pour ne pas encombrer l'affichage.
	 * Limite a 4 raisons maximum.
	 */
	function rankingReason(rs: RankingSignals): { label: string; contribution: number }[] {
		const reasons: { label: string; contribution: number }[] = [];
		if (rs.text_score > 0) {
			reasons.push({ label: 'Mots de la recherche dans le titre ou la description', contribution: rs.text_score * rs.weight_text });
		}
		if (rs.quality_normalized > 0) {
			reasons.push({ label: 'Qualite technique des metadonnees', contribution: rs.quality_normalized * rs.weight_quality });
		}
		if (rs.freshness_component > 0) {
			reasons.push({ label: 'Fraicheur des donnees', contribution: rs.freshness_component * rs.weight_freshness });
		}
		reasons.sort((a, b) => b.contribution - a.contribution);
		return reasons.slice(0, 4);
	}

	const visibleTags = $derived(dataset.tags.slice(0, MAX_TAGS));
	const hasMoreTags = $derived(dataset.tags.length > MAX_TAGS);
	const safeFormats = $derived(dataset.resource_formats.length > 0 ? dataset.resource_formats : ['Non renseigne']);
	const datasetLink = $derived(
		appendSearchContext(`/dataset/${encodeURIComponent(dataset.id)}`, searchContext)
	);
	const datasetApiLink = $derived(`/api/v1/dataset/${encodeURIComponent(dataset.id)}`);
	const rankingReasons = $derived(dataset.ranking_signals ? rankingReason(dataset.ranking_signals) : []);
	const ponderationLink = $derived(
		appendSearchContext(`/dataset/${encodeURIComponent(dataset.id)}/ponderation`, searchContext)
	);
</script>

<article class="dataset-card" aria-labelledby={`dataset-title-${dataset.id}`}>
	<header class="dataset-head">
		<div class="title-row">
			<h3 id={`dataset-title-${dataset.id}`}>{dataset.title}</h3>
			<label class="compare-check">
				<input
					type="checkbox"
					checked={isCompared}
					disabled={compareDisabled && !isCompared}
					onchange={() => onToggleCompare(dataset.id)}
					aria-label={isCompared ? `Retirer ${dataset.title} de la comparaison` : `Ajouter ${dataset.title} a la comparaison`}
				/>
				<span>Comparer</span>
			</label>
		</div>
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

	{#if dataset.ranking_signals}
		<section class="ranking" aria-label="Pourquoi ce resultat">
			<h4>Score de pertinence : {percentLabel(dataset.ranking_signals.hybrid_score)}</h4>
			<ol class="ranking-reasons">
				{#each rankingReasons as reason, idx (`${reason.label}-${idx}`)}
					<li>
						<span class="reason-bar" style="width: {Math.round(reason.contribution * 100)}%"></span>
						<span class="reason-text">{reason.label} ({percentLabel(reason.contribution)})</span>
					</li>
				{/each}
			</ol>
			<p class="ranking-note">
				<a href={ponderationLink}>Comprendre le calcul du score</a>
			</p>
		</section>
	{/if}

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

	.title-row {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-2);
	}

	.compare-check {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		font-size: var(--font-size-ui);
		font-weight: 600;
		cursor: pointer;
		white-space: nowrap;
		flex-shrink: 0;
	}

	.compare-check input[type="checkbox"] {
		width: 1.25rem;
		height: 1.25rem;
		accent-color: var(--color-primary);
		cursor: pointer;
	}

	.compare-check input[type="checkbox"]:disabled {
		opacity: 0.4;
		cursor: not-allowed;
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

	.ranking {
		display: grid;
		gap: var(--space-2);
		padding: var(--space-3);
		background: color-mix(in oklch, var(--color-success) 12%, var(--color-surface-muted));
		border: var(--border-thin) solid var(--color-success);
		border-radius: var(--radius-none);
	}

	.ranking h4 {
		margin: 0;
		font-size: var(--font-size-heading-sm);
		font-weight: 700;
	}

	.ranking-reasons {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--space-2);
	}

	.ranking-reasons li {
		position: relative;
		padding: var(--space-1) var(--space-2);
		font-size: var(--font-size-ui);
		background: var(--color-surface);
		border: var(--border-thin) solid var(--color-border);
		overflow: hidden;
	}

	.reason-bar {
		position: absolute;
		inset: 0;
		background: color-mix(in oklch, var(--color-success) 30%, transparent);
		z-index: 0;
	}

	.reason-text {
		position: relative;
		z-index: 1;
	}

	.ranking-note {
		font-size: var(--font-size-ui);
	}

	.ranking-note a {
		font-weight: 600;
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
