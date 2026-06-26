<script lang="ts">
	import { env } from '$env/dynamic/public';
	import { replaceState } from '$app/navigation';
	import { onMount } from 'svelte';

	import { Button, Card, CardDataset, CompareBar, FiltersPanel, SkeletonCard, StateBadge } from '$lib';
	import { normalizeSearchContext } from '$lib/navigation/search-context';
	import type { SearchDatasetItem, FacetItem, SearchResponse } from '$lib/types/search';

	type SortValue =
		| 'modified_desc'
		| 'modified_asc'
		| 'quality_desc'
		| 'quality_asc'
		| 'hybrid'
		| 'title_asc'
		| 'title_desc';

	const PAGE_SIZE = 10;
	const sortLabels: Record<SortValue, string> = {
		modified_desc: 'Date (plus recent)',
		modified_asc: 'Date (plus ancien)',
		quality_desc: 'Qualite (meilleure)',
		quality_asc: 'Qualite (moins bonne)',
		hybrid: 'Pertinence (hybride)',
		title_asc: 'Nom (A-Z)',
		title_desc: 'Nom (Z-A)'
	};
	const sortOptions = Object.entries(sortLabels).map(([value, label]) => ({ value, label }));

	let query = $state('');
	let sort = $state<SortValue>('modified_desc');
	let selectedOrg = $state('');
	let selectedFormat = $state('');
	let selectedTag = $state('');
	let currentPage = $state(1);
	let isLoading = $state(false);
	let errorMessage = $state('');
	let data = $state<SearchResponse | null>(null);
	let resultHeading = $state<HTMLParagraphElement | null>(null);

	// Etat comparaison guidee (PDS-43)
	const MAX_COMPARE = 4;
	let compareIds = $state<string[]>([]);
	const compareDisabled = $derived(compareIds.length >= MAX_COMPARE);

	function toggleCompare(id: string): void {
		const idx = compareIds.indexOf(id);
		if (idx >= 0) {
			compareIds = compareIds.filter((cid) => cid !== id);
		} else if (compareIds.length < MAX_COMPARE) {
			compareIds = [...compareIds, id];
		}
	}

	function clearCompare(): void {
		compareIds = [];
	}

	function navigateToCompare(): void {
		const ids = compareIds.join(',');
		window.location.href = `/comparer?ids=${encodeURIComponent(ids)}`;
	}

	const totalPages = $derived.by(() => {
		if (!data) {
			return 1;
		}
		return Math.max(1, Math.ceil(data.total / data.limit));
	});

	const canGoPrev = $derived(currentPage > 1);
	const canGoNext = $derived(currentPage < totalPages);
	const activeFilterCount = $derived(
		(selectedOrg ? 1 : 0) + (selectedFormat ? 1 : 0) + (selectedTag ? 1 : 0)
	);

	const organizations = $derived.by(() => data?.facets?.organizations ?? []);
	const formats = $derived.by(() => data?.facets?.formats ?? []);
	const tags = $derived.by(() => data?.facets?.tags ?? []);

	const useMockApi = env.PUBLIC_USE_MOCK_API === '1';
	const apiBase = useMockApi ? '' : (env.PUBLIC_API_BASE_URL || '');
	const searchContext = $derived.by(() => normalizeSearchContext(buildSearchStateParams().toString()));

	function safeTrim(value: string): string {
		return value.trim();
	}

	function buildSearchStateParams(): URLSearchParams {
		const params = new URLSearchParams();
		const textQuery = safeTrim(query);

		if (textQuery.length > 0) {
			params.set('q', textQuery);
		}
		if (sort !== 'modified_desc') {
			params.set('sort', sort);
		}
		if (currentPage > 1) {
			params.set('page', String(currentPage));
		}
		if (selectedOrg) {
			params.set('org', selectedOrg);
		}
		if (selectedFormat) {
			params.set('fmt', selectedFormat);
		}
		if (selectedTag) {
			params.set('tag', selectedTag);
		}

		return params;
	}

	function syncUrlState(): void {
		const params = buildSearchStateParams();

		const queryString = params.toString();
		const nextUrl = queryString.length > 0 ? `${window.location.pathname}?${queryString}` : window.location.pathname;
		replaceState(nextUrl, {});
	}

	function hydrateStateFromUrl(): void {
		const params = new URLSearchParams(window.location.search);
		const urlSort = params.get('sort');
		const urlPage = params.get('page');

		query = params.get('q') ?? '';
		selectedOrg = params.get('org') ?? '';
		selectedFormat = params.get('fmt') ?? '';
		selectedTag = params.get('tag') ?? '';

		if (urlSort && urlSort in sortLabels) {
			sort = urlSort as SortValue;
		}

		if (urlPage) {
			const parsed = Number.parseInt(urlPage, 10);
			if (Number.isFinite(parsed) && parsed > 0) {
				currentPage = parsed;
			}
		}
	}

	function buildSearchUrl(): string {
		const params = new URLSearchParams({
			offset: String((currentPage - 1) * PAGE_SIZE),
			limit: String(PAGE_SIZE),
			sort
		});
		const textQuery = safeTrim(query);
		if (textQuery.length > 0) {
			params.set('q', textQuery);
		}
		if (selectedOrg) {
			params.set('org', selectedOrg);
		}
		if (selectedFormat) {
			params.set('fmt', selectedFormat);
		}
		if (selectedTag) {
			params.set('tag', selectedTag);
		}
		return `${apiBase}/api/v1/search?${params.toString()}`;
	}

	async function runSearch(): Promise<void> {
		isLoading = true;
		errorMessage = '';
		try {
			const response = await fetch(buildSearchUrl());
			if (!response.ok) {
				throw new Error(`Erreur API ${response.status}`);
			}
			data = (await response.json()) as SearchResponse;
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
			data = null;
		} finally {
			syncUrlState();
			isLoading = false;
			if (resultHeading) {
				requestAnimationFrame(() => resultHeading?.focus());
			}
		}
	}

	async function submitSearch(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		currentPage = 1;
		await runSearch();
	}

	async function changeSort(event: Event): Promise<void> {
		sort = (event.currentTarget as HTMLSelectElement).value as SortValue;
		currentPage = 1;
		await runSearch();
	}

	async function changeFacet(event: Event, facet: 'org' | 'fmt' | 'tag'): Promise<void> {
		const value = (event.currentTarget as HTMLSelectElement).value;
		if (facet === 'org') {
			selectedOrg = value;
		}
		if (facet === 'fmt') {
			selectedFormat = value;
		}
		if (facet === 'tag') {
			selectedTag = value;
		}
		currentPage = 1;
		await runSearch();
	}

	async function clearAllFilters(): Promise<void> {
		selectedOrg = '';
		selectedFormat = '';
		selectedTag = '';
		currentPage = 1;
		await runSearch();
	}

	async function goToPage(page: number): Promise<void> {
		if (page < 1 || page > totalPages) {
			return;
		}
		currentPage = page;
		await runSearch();
	}

	onMount(async () => {
		hydrateStateFromUrl();
		await runSearch();
	});
</script>

<svelte:head>
	<title>Recherche - PDS Portail</title>
</svelte:head>

<section class="stack">
	<Card title="Recherche datasets" subtitle="Appels reels sur le contrat backend PDS-6bis">
		<div class="badges" aria-label="Etats interface">
			<StateBadge label="Pret" variant="info" />
			<StateBadge label="Tri actif" variant="success" />
			<StateBadge label="Pagination" variant="warning" />
			<StateBadge label="Erreur" variant="danger" />
		</div>

		<FiltersPanel
				bind:query
				bind:sort
				bind:selectedOrg
				bind:selectedFormat
				bind:selectedTag
				{activeFilterCount}
				{organizations}
				{formats}
				{tags}
				{sortOptions}
				onSubmit={submitSearch}
				onSortChange={changeSort}
				onFacetChange={changeFacet}
				onClearQuery={async () => {
					query = '';
					currentPage = 1;
					await runSearch();
				}}
				onClearFilters={clearAllFilters}
			/>
	</Card>

	{#if isLoading}
		<div role="status" aria-live="polite" aria-label="Chargement des resultats">
			<ul class="results">
				{#each Array(3) as _}
					<li><SkeletonCard /></li>
				{/each}
			</ul>
		</div>
	{:else if errorMessage}
		<p class="state state-danger" role="alert">Echec recherche: {errorMessage}</p>
	{:else if data && data.datasets.length > 0}
		<p class="state state-success" tabindex="-1" bind:this={resultHeading}>
			{data.total} resultats trouves.
		</p>
		<ul class="results" aria-label="Resultats de recherche">
			{#each data.datasets as dataset (dataset.id)}
				<li>
					<CardDataset
						{dataset}
						{searchContext}
						isCompared={compareIds.includes(dataset.id)}
						compareDisabled={compareDisabled}
						onToggleCompare={toggleCompare}
					/>
				</li>
			{/each}
		</ul>

		<nav class="pagination" aria-label="Pagination resultats">
			<Button
				label="Precedent"
				variant="ghost"
				disabled={!canGoPrev}
				onclick={async () => {
					await goToPage(currentPage - 1);
				}}
			/>
			<p>Page {currentPage} / {totalPages}</p>
			<Button
				label="Suivant"
				variant="ghost"
				disabled={!canGoNext}
				onclick={async () => {
					await goToPage(currentPage + 1);
				}}
			/>
		</nav>
	{:else}
		<p class="state">Aucun resultat charge pour le moment.</p>
	{/if}

	<CompareBar
		{compareIds}
		onClear={clearCompare}
		onCompare={navigateToCompare}
	/>

	{#if data?.facets}
		<Card title="Facettes" subtitle="Aide a la navigation des resultats">
			<div class="facets-grid">
				<section>
					<h3>Organisations</h3>
					<ul>
						{#each data.facets.organizations.slice(0, 5) as facet (facet.name)}
							<li>{facet.display_name ?? facet.name} ({facet.count})</li>
						{/each}
					</ul>
				</section>
				<section>
					<h3>Formats</h3>
					<ul>
						{#each data.facets.formats.slice(0, 5) as facet (facet.name)}
							<li>{facet.name} ({facet.count})</li>
						{/each}
					</ul>
				</section>
			</div>
		</Card>
	{/if}
</section>

<style>
	.stack {
		display: grid;
		gap: var(--space-4);
	}


	.badges {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		margin-bottom: var(--space-3);
	}

	.state {
		margin: 0;
		padding: var(--space-3) var(--space-4);
		background: var(--color-surface-muted);
		border: var(--border-thin) dashed var(--color-border);
		border-radius: var(--radius-none);
		color: var(--color-on-surface);
	}

	.state-danger {
		background: var(--color-danger);
		border-color: var(--color-danger);
		color: var(--color-on-danger);
		opacity: 1;
	}

	.state-success {
		background: var(--color-success);
		border-color: var(--color-success);
		color: var(--color-on-success);
		opacity: 1;
	}

	.results {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: var(--space-3);
	}

	.pagination {
		margin-top: var(--space-3);
		display: flex;
		align-items: center;
		gap: var(--space-3);
		flex-wrap: wrap;
	}

	.pagination p {
		margin: 0;
	}

	.facets-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: var(--space-4);
	}

	.facets-grid h3 {
		margin: 0 0 var(--space-2);
		font-size: var(--font-size-heading-sm);
	}

	.facets-grid ul {
		margin: 0;
		padding-left: var(--space-4);
	}

	@media (max-width: 43.75rem) {
		.pagination {
			display: grid;
			grid-template-columns: 1fr 1fr;
			gap: var(--space-3);
		}

		.pagination p {
			grid-column: 1 / -1;
		}
	}
</style>