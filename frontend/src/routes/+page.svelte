<script lang="ts">
	import { onMount } from 'svelte';
	import { fade } from 'svelte/transition';

	import { Button, Card, CardDataset, CompareBar, EmptyState, FiltersPanel, PageLayout, SkeletonCard, StateBadge } from '$lib';
	import { useSearch, sortOptions, sortLabels } from '$lib/runes/search.svelte';

	const search = useSearch();
	let resultHeading = $state<HTMLParagraphElement | null>(null);

	onMount(async () => {
		await search.init(resultHeading);
	});
</script>

<svelte:head>
	<title>Recherche - PDS Portail</title>
</svelte:head>

<PageLayout>
	<Card title="Recherche datasets">
		<div class="badges" aria-label="Etats de l'interface" role="status" aria-live="polite">
			<StateBadge label={search.readyLabel} variant={search.readyState} />
			<StateBadge label={search.sortLabel} variant="info" />
			<StateBadge label={search.pageLabel} variant="warning" />
			{#if search.errorMessage}
				<StateBadge label={search.errorMessage} variant="danger" />
			{/if}
		</div>

		<FiltersPanel
				bind:query={search.query}
				bind:sort={search.sort}
				bind:selectedOrg={search.selectedOrg}
				bind:selectedFormat={search.selectedFormat}
				bind:selectedTags={search.selectedTags}
				activeFilterCount={search.activeFilterCount}
				organizations={search.organizations}
				formats={search.formats}
				tags={search.tags}
				{sortOptions}
				onSubmit={(e) => search.submitSearch(e, resultHeading)}
				onSortChange={search.changeSort}
				onFacetChange={search.changeFacet}
				onQueryChange={(q) => search.handleQueryChange(q, resultHeading)}
				onClearQuery={() => search.handleQueryChange('', resultHeading)}
				onClearFilters={search.clearAllFilters}
			/>
	</Card>

	{#if search.isLoading}
		<div role="status" aria-live="polite" aria-label="Chargement des résultats">
			<ul class="results">
				{#each Array(3) as _, idx (`skeleton-${idx}`)}
					<li><SkeletonCard /></li>
				{/each}
			</ul>
		</div>
	{:else if search.errorMessage}
		<EmptyState
			variant="error"
			title="Impossible de lancer la recherche"
			description="Verifiez votre connexion et reessayez. {search.errorMessage}"
		/>
	{:else if search.data && search.data.datasets.length > 0}
		{#key search.resultsKey}
			<div class="results-wrapper" in:fade={{ duration: 300 }} out:fade={{ duration: 150 }}>
				<p class="results-summary" tabindex="-1" bind:this={resultHeading}>
					{search.data.total} résultats trouvés.
				</p>
				<ul class="results" aria-label="Résultats de recherche">
					{#each search.data.datasets as dataset (dataset.id)}
						<li>
							<CardDataset
								{dataset}
								searchContext={search.searchContext}
								isCompared={search.compareIds.includes(dataset.id)}
								compareDisabled={search.compareDisabled}
								onToggleCompare={search.toggleCompare}
							/>
						</li>
					{/each}
				</ul>
			</div>
		{/key}

		<nav class="pagination" aria-label="Pagination résultats">
			<Button
				label="Précédent"
				variant="ghost"
				disabled={!search.canGoPrev}
				onclick={async () => {
					await search.goToPage(search.currentPage - 1, resultHeading);
				}}
			/>
			<p>Page {search.currentPage} / {search.totalPages}</p>
			<Button
				label="Suivant"
				variant="ghost"
				disabled={!search.canGoNext}
				onclick={async () => {
					await search.goToPage(search.currentPage + 1, resultHeading);
				}}
			/>
		</nav>
	{:else}
		<EmptyState
			title="Aucun résultat pour cette recherche"
			description="Essayez de modifier vos filtres ou votre terme de recherche."
		/>
	{/if}

	<CompareBar
		compareIds={search.compareIds}
		onClear={search.clearCompare}
		onCompare={search.navigateToCompare}
	/>

	{#if search.data?.facets}
		<Card title="Facettes" subtitle="Aide à la navigation des résultats">
			<div class="facets-grid">
				<section>
					<h3>Organisations</h3>
					<ul>
						{#each search.data.facets.organizations.slice(0, 5) as facet, idx (`${facet.name}-${idx}`)}
							<li>{facet.display_name ?? facet.name} ({facet.count})</li>
						{/each}
					</ul>
				</section>
				<section>
					<h3>Formats</h3>
					<ul>
						{#each search.data.facets.formats.slice(0, 5) as facet, idx (`${facet.name}-${idx}`)}
							<li>{facet.name} ({facet.count})</li>
						{/each}
					</ul>
				</section>
			</div>
		</Card>
	{/if}
</PageLayout>

<style>

	.badges {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		margin-bottom: var(--space-3);
	}

	.results-summary {
		margin: 0;
		padding: var(--space-3) var(--space-4);
		background: var(--color-success);
		border: var(--border-thin) solid var(--color-success);
		border-radius: var(--radius-none);
		color: var(--color-on-success);
		font-weight: 600;
		max-width: none;
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