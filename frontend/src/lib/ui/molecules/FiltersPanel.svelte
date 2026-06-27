<script lang="ts">
	import Button from '../atoms/Button.svelte';
	import Input from '../atoms/Input.svelte';

	export type FacetItem = {
		name: string;
		count: number;
		display_name?: string;
	};

	let {
		query = $bindable(''),
		sort = $bindable('modified_desc'),
		selectedOrg = $bindable(''),
		selectedFormat = $bindable(''),
		selectedTag = $bindable(''),
		activeFilterCount = 0,
		organizations = [],
		formats = [],
		tags = [],
		sortOptions = [],
		onSubmit,
		onSortChange,
		onFacetChange,
		onClearQuery,
		onClearFilters
	}: {
		query?: string;
		sort?: string;
		selectedOrg?: string;
		selectedFormat?: string;
		selectedTag?: string;
		activeFilterCount?: number;
		organizations?: FacetItem[];
		formats?: FacetItem[];
		tags?: FacetItem[];
		sortOptions?: Array<{ value: string; label: string }>;
		onSubmit: (event: SubmitEvent) => Promise<void> | void;
		onSortChange: (event: Event) => Promise<void> | void;
		onFacetChange: (event: Event, facet: 'org' | 'fmt' | 'tag') => Promise<void> | void;
		onClearQuery: () => Promise<void> | void;
		onClearFilters: () => Promise<void> | void;
	} = $props();

	/**
	 * Met a jour immediatement la variable bindable ET notifie le parent.
	 * Chaque facette a son propre timer pour permettre les changements rapides
	 * sans perdre de selection (ex: changer Org puis Format avant debounce).
	 */
	const facetTimers: Record<string, ReturnType<typeof setTimeout> | null> = {};

	function immediateFacetChange(event: Event, facet: 'org' | 'fmt' | 'tag'): void {
		const target = event.currentTarget as HTMLSelectElement;
		const value = target.value;

		// Mise a jour immediate de la variable bindable locale
		if (facet === 'org') selectedOrg = value;
		if (facet === 'fmt') selectedFormat = value;
		if (facet === 'tag') selectedTag = value;

		// Debounce independant par facette pour eviter les appels API en rafale
		if (facetTimers[facet]) clearTimeout(facetTimers[facet]!);
		facetTimers[facet] = setTimeout(() => {
			onFacetChange({ currentTarget: { value } } as unknown as Event, facet);
		}, 300);
	}

	const sortTimer: { current: ReturnType<typeof setTimeout> | null } = { current: null };

	function immediateSortChange(event: Event): void {
		const target = event.currentTarget as HTMLSelectElement;
		const value = target.value;

		// Mise a jour immediate
		sort = value;

		if (sortTimer.current) clearTimeout(sortTimer.current);
		sortTimer.current = setTimeout(() => {
			onSortChange({ currentTarget: { value } } as unknown as Event);
		}, 300);
	}

	function optionList(items: FacetItem[], selectedValue: string): FacetItem[] {
		// Dedoublonne par nom pour eviter each_key_duplicate
		const seen = new Set<string>();
		const deduped = items.filter((item) => {
			if (seen.has(item.name)) return false;
			seen.add(item.name);
			return true;
		});

		if (!selectedValue || seen.has(selectedValue)) {
			return deduped;
		}
		return [{ name: selectedValue, count: 0, display_name: selectedValue }, ...deduped];
	}
</script>

<form class="search" onsubmit={onSubmit}>
	<Input id="q" label="Rechercher" bind:value={query} placeholder="ex: mobilite, geographie" />

	<fieldset class="facets-toolbar">
		<legend>Filtres facettes</legend>
		<label class="select-field" for="facet-org">
			<span>Organisation</span>
			<select id="facet-org" value={selectedOrg} onchange={(event) => immediateFacetChange(event, 'org')}>
				<option value="">Toutes</option>
				{#each optionList(organizations, selectedOrg) as facet (facet.name)}
					<option value={facet.name}>{facet.display_name ?? facet.name} ({facet.count})</option>
				{/each}
			</select>
		</label>

		<label class="select-field" for="facet-format">
			<span>Format</span>
			<select id="facet-format" value={selectedFormat} onchange={(event) => immediateFacetChange(event, 'fmt')}>
				<option value="">Tous</option>
				{#each optionList(formats, selectedFormat) as facet (facet.name)}
					<option value={facet.name}>{facet.name} ({facet.count})</option>
				{/each}
			</select>
		</label>

		<label class="select-field" for="facet-tag">
			<span>Categorie / tag</span>
			<select id="facet-tag" value={selectedTag} onchange={(event) => immediateFacetChange(event, 'tag')}>
				<option value="">Tous</option>
				{#each optionList(tags, selectedTag) as facet (facet.name)}
					<option value={facet.name}>{facet.name} ({facet.count})</option>
				{/each}
			</select>
		</label>
	</fieldset>

	<p class="filters-meta" aria-live="polite">Filtres actifs: {activeFilterCount}</p>

	<label class="select-field" for="sort">
		<span>Tri</span>
		<select id="sort" value={sort} onchange={(event) => immediateSortChange(event)}>
			{#each sortOptions as option (option.value)}
				<option value={option.value}>{option.label}</option>
			{/each}
		</select>
	</label>

	<div class="actions">
		<Button label="Rechercher" type="submit" />
		<Button label="Effacer" variant="ghost" onclick={onClearQuery} />
		<Button
			label="Vider les filtres"
			variant="ghost"
			disabled={activeFilterCount === 0}
			onclick={onClearFilters}
		/>
	</div>
</form>

<style>
	.search {
		display: grid;
		gap: var(--space-3);
	}

	.facets-toolbar {
		display: grid;
		gap: var(--space-3);
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		margin: 0;
		padding: 0;
		border: 0;
	}

	.facets-toolbar legend {
		font-weight: 700;
		font-size: var(--font-size-ui);
		margin-bottom: var(--space-1);
	}

	.filters-meta {
		margin: 0;
		font-size: var(--font-size-ui);
		color: var(--color-on-surface-subtle);
	}

	.select-field {
		display: grid;
		gap: var(--space-2);
		font-size: var(--font-size-ui);
	}

	.select-field span {
		font-weight: 600;
		color: var(--color-on-surface-subtle);
	}

	.select-field select {
		border: var(--border-thin) solid var(--color-border);
		background: var(--color-surface);
		border-radius: var(--radius-none);
		padding: var(--space-3) var(--space-4);
		min-height: var(--size-control-md);
		color: var(--color-on-surface);
	}

	.select-field select:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	.actions {
		display: flex;
		gap: var(--space-3);
		flex-wrap: wrap;
	}

	@media (max-width: 43.75rem) {
		.actions {
			display: grid;
			grid-template-columns: 1fr;
		}

		.actions :global(button) {
			width: 100%;
		}
	}
</style>
