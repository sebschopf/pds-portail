<script lang="ts">
	import { onMount } from 'svelte';
	import Button from '../atoms/Button.svelte';
	import Input from '../atoms/Input.svelte';
	import Skeleton from '../atoms/Skeleton.svelte';
	import DatasetIcon from '../../assets/icons/DatasetIcon.svelte';

	type ColumnStats = {
		min: number | null;
		max: number | null;
		mean: number | null;
		median: number | null;
	};

	type ColumnInfo = {
		name: string;
		detected_type: string;
		fill_rate: number;
		sample_values: string[];
		stats: ColumnStats | null;
	};

	type ResourceAnalysis = {
		summary: string;
		capabilities: string[];
		caveats: string[];
	};

	type ExploreResponse = {
		resource_id: string;
		format: string;
		parsed_at: string;
		columns: ColumnInfo[];
		row_count: number;
		analysis: ResourceAnalysis | null;
		cached: boolean;
	};

	type ExploreUiState = 'locked' | 'loading' | 'error' | 'success';

	const STORAGE_KEY = 'pds-explore-key';

	let { resourceId }: { resourceId: string } = $props();

	let apiKey = $state('');
	let uiState = $state<ExploreUiState>('locked');
	let errorMessage = $state('');
	let exploreResult = $state<ExploreResponse | null>(null);

	const hasApiKey = $derived(apiKey.trim().length > 0);
	const numericColumns = $derived(
		exploreResult?.columns.filter((column) => column.stats !== null) ?? []
	);

	function formatPercent(value: number): string {
		const percent = Math.round(value * 1000) / 10;
		return `${percent}%`;
	}

	function formatNumber(value: number | null): string {
		if (value === null || Number.isNaN(value)) {
			return 'N/A';
		}
		return new Intl.NumberFormat('fr-CH', {
			maximumFractionDigits: 2
		}).format(value);
	}

	function mapError(status: number, detail: string | null): string {
		if (status === 401) {
			return 'Clé API invalide ou manquante. Vérifiez votre clé puis réessayez.';
		}
		if (status === 429) {
			return 'Quota mensuel épuisé pour cette clé API.';
		}
		if (status === 422) {
			return detail ?? 'Format non supporté pour cette ressource.';
		}
		if (status === 504) {
			return 'Le téléchargement de la ressource a expiré (timeout). Réessayez plus tard.';
		}
		return detail ?? `Erreur API ${status}`;
	}

	async function runExplore(keyToUse: string): Promise<void> {
		if (!keyToUse.trim()) {
			uiState = 'error';
			errorMessage = 'Veuillez saisir une clé API.';
			return;
		}

		uiState = 'loading';
		errorMessage = '';

		const response = await fetch(`/api/v1/resources/${encodeURIComponent(resourceId)}/explore`, {
			method: 'POST',
			headers: {
				'X-API-Key': keyToUse
			}
		});

		if (!response.ok) {
			let detail: string | null = null;
			try {
				const errorPayload = (await response.json()) as { detail?: string };
				detail = errorPayload.detail ?? null;
			} catch {
				detail = null;
			}

			uiState = 'error';
			errorMessage = mapError(response.status, detail);
			return;
		}

		const payload = (await response.json()) as ExploreResponse;
		exploreResult = payload;
		uiState = 'success';
		localStorage.setItem(STORAGE_KEY, keyToUse);
	}

	function onSubmitExplore(event: SubmitEvent): void {
		event.preventDefault();
		void runExplore(apiKey);
	}

	function onInputKeyDown(event: KeyboardEvent): void {
		if (event.key === 'Escape') {
			event.preventDefault();
			errorMessage = '';
			uiState = 'locked';
		}
	}

	onMount(() => {
		const storedKey = localStorage.getItem(STORAGE_KEY);
		if (!storedKey) {
			return;
		}

		apiKey = storedKey;
		void runExplore(storedKey);
	});
</script>

<section class="explore" aria-label="Exploration des champs">
	<header class="explore-header">
		<h4>Exploration des champs</h4>
		<p class="description">
			Saisissez votre clé d'accès premium pour analyser automatiquement la structure du fichier.
		</p>
	</header>

	<form class="unlock" onsubmit={onSubmitExplore}>
		<Input
			id={`explore-key-${resourceId}`}
			label="Clé API premium"
			placeholder="Ex: pds_live_xxxxx"
			bind:value={apiKey}
			required={true}
			autocomplete="off"
			onkeydown={onInputKeyDown}
		/>
		<Button label="Debloquer l'exploration" type="submit" disabled={!hasApiKey || uiState === 'loading'} />
	</form>

	{#if uiState === 'loading'}
		<div class="loading" role="status" aria-live="polite">
			<p>Analyse du fichier en cours...</p>
			<div class="skeleton-grid">
				<Skeleton width="100%" height="1.1rem" ariaLabel="Chargement ligne 1" />
				<Skeleton width="100%" height="1.1rem" ariaLabel="Chargement ligne 2" />
				<Skeleton width="100%" height="1.1rem" ariaLabel="Chargement ligne 3" />
			</div>
		</div>
	{:else if uiState === 'error'}
		<p class="error" role="alert">{errorMessage}</p>
	{:else if uiState === 'success' && exploreResult}
		<section class="results" aria-label="Resultats de l'exploration">
			<p class="meta">
				Format: <strong>{exploreResult.format.toUpperCase()}</strong> - Lignes: <strong>{exploreResult.row_count}</strong>
				{#if exploreResult.cached}
					<span class="cached" aria-label="Resultat issu du cache">(resultat en cache)</span>
				{/if}
			</p>

			<div class="table-wrapper">
				<table>
					<caption>Colonnes detectees pour la ressource</caption>
					<thead>
						<tr>
							<th scope="col">Nom</th>
							<th scope="col">Type</th>
							<th scope="col">Remplissage</th>
							<th scope="col">Echantillons</th>
						</tr>
					</thead>
					<tbody>
						{#each exploreResult.columns as column (column.name)}
							<tr>
								<td>{column.name}</td>
								<td>{column.detected_type}</td>
								<td>{formatPercent(column.fill_rate)}</td>
								<td>{column.sample_values.join(', ') || 'N/A'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			{#if numericColumns.length > 0}
				<section class="stats" aria-label="Statistiques numeriques">
					<h5>Cartes resume statistiques</h5>
					<div class="cards">
						{#each numericColumns as column (column.name)}
							<article class="card">
								<h6>{column.name}</h6>
								<ul>
									<li>Min: {formatNumber(column.stats?.min ?? null)}</li>
									<li>Max: {formatNumber(column.stats?.max ?? null)}</li>
									<li>Moyenne: {formatNumber(column.stats?.mean ?? null)}</li>
									<li>Mediane: {formatNumber(column.stats?.median ?? null)}</li>
								</ul>
							</article>
						{/each}
					</div>
				</section>
			{/if}

			{#if exploreResult.analysis}
				<section class="analysis" aria-label="Analyse heuristique">
					<div class="analysis-title">
						<DatasetIcon size="20" label="Analyse dataset" />
						<h5>Analyse</h5>
					</div>
					<p>{exploreResult.analysis.summary}</p>

					<div class="analysis-lists">
						<div>
							<h6>Capacites</h6>
							<ul>
								{#each exploreResult.analysis.capabilities as item (`capability-${item}`)}
									<li>{item}</li>
								{/each}
							</ul>
						</div>
						<div>
							<h6>Points d'attention</h6>
							<ul>
								{#each exploreResult.analysis.caveats as item (`caveat-${item}`)}
									<li>{item}</li>
								{/each}
							</ul>
						</div>
					</div>
				</section>
			{/if}
		</section>
	{/if}
</section>

<style>
	.explore {
		margin-top: var(--space-5);
		padding: var(--space-4);
		border: var(--border-thin) solid var(--color-border);
		background: var(--color-surface-muted);
		display: grid;
		gap: var(--space-4);
	}

	.explore-header h4 {
		margin: 0;
		font-size: var(--font-size-heading-sm);
	}

	.description {
		margin: var(--space-2) 0 0;
		color: var(--color-on-surface-soft);
	}

	.unlock {
		display: grid;
		gap: var(--space-3);
	}

	.loading p {
		margin: 0;
		font-weight: 600;
	}

	.skeleton-grid {
		margin-top: var(--space-3);
		display: grid;
		gap: var(--space-2);
	}

	.error {
		margin: 0;
		padding: var(--space-3);
		border: var(--border-thin) solid var(--color-danger);
		background: color-mix(in oklch, var(--color-danger) 10%, var(--color-surface));
		color: var(--color-danger);
		font-weight: 600;
	}

	.meta {
		margin: 0;
		font-size: var(--font-size-ui);
	}

	.cached {
		color: var(--color-on-surface-soft);
	}

	.table-wrapper {
		overflow-x: auto;
		border: var(--border-thin) solid var(--color-border);
		background: var(--color-surface);
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--font-size-ui);
	}

	caption {
		text-align: left;
		font-weight: 700;
		padding: var(--space-3);
		background: var(--color-surface-muted);
	}

	th,
	td {
		padding: var(--space-2) var(--space-3);
		border-top: var(--border-thin) solid var(--color-border);
		vertical-align: top;
	}

	th {
		text-align: left;
		font-weight: 700;
	}

	.stats h5,
	.analysis h5,
	.analysis h6 {
		margin: 0;
	}

	.cards {
		margin-top: var(--space-3);
		display: grid;
		gap: var(--space-3);
		grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
	}

	.card {
		border: var(--border-thin) solid var(--color-border);
		background: var(--color-surface);
		padding: var(--space-3);
	}

	.card h6 {
		margin: 0;
		font-size: var(--font-size-ui);
	}

	.card ul {
		margin: var(--space-2) 0 0;
		padding-left: var(--space-4);
		display: grid;
		gap: var(--space-1);
	}

	.analysis {
		padding: var(--space-3);
		border: var(--border-thin) solid var(--color-border);
		background: var(--color-surface);
		display: grid;
		gap: var(--space-3);
	}

	.analysis-title {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.analysis p {
		margin: 0;
	}

	.analysis-lists {
		display: grid;
		gap: var(--space-3);
		grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
	}

	.analysis ul {
		margin: var(--space-2) 0 0;
		padding-left: var(--space-4);
		display: grid;
		gap: var(--space-1);
	}

	@media (max-width: 43.75rem) {
		.explore {
			padding: var(--space-3);
		}
	}
</style>
