<script lang="ts">
	import Button from '../atoms/Button.svelte';
	import Input from '../atoms/Input.svelte';

	export type FacetItem = {
		name: string;
		count: number;
		display_name?: string;
	};

	const DEBOUNCE_MS = 300;

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

	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	function debouncedFacetChange(event: Event, facet: 'org' | 'fmt' | 'tag'): void {
		if (debounceTimer) clearTimeout(debounceTimer);
		// Capturer la valeur immediatement : l'event Svelte est recycle apres le handler
		const target = event.currentTarget as HTMLSelectElement;
		const value = target.value;
		debounceTimer = setTimeout(() => {
			onFacetChange({ currentTarget: { value } } as unknown as Event, facet);
		}, DEBOUNCE_MS);
	}

	function debouncedSortChange(event: Event): void {
		if (debounceTimer) clearTimeout(debounceTimer);
		const target = event.currentTarget as HTMLSelectElement;
		const value = target.value;
		debounceTimer = setTimeout(() => {
			onSortChange({ currentTarget: { value } } as unknown as Event);
		}, DEBOUNCE_MS);
	}

	function optionList(items: FacetItem[], selectedValue: string): FacetItem[] {
		if (!selectedValue || items.some((item) => item.name === selectedValue)) {
			return items;
		}
		return [{ name: selectedValue, count: 0, display_name: selectedValue }, ...items];
	}
</script>

<form class="search" onsubmit={onSubmit}>
	<Input id="q" label="Rechercher" bind:value={query} placeholder="ex: mobilite, geographie" />

	<fieldset class="facets-toolbar">
		<legend>Filtres facettes</legend>
		<label class="select-field" for="facet-org">
			<span>Organisation</span>
			<select id="facet-org" value={selectedOrg} onchange={(event) => debouncedFacetChange(event, 'org')}>
				<option value="">Toutes</option>
				{#each optionList(organizations, selectedOrg) as facet (facet.name)}
					<option value={facet.name}>{facet.display_name ?? facet.name} ({facet.count})</option>
				{/each}
			</select>
		</label>

		<label class="select-field" for="facet-format">
			<span>Format</span>
			<select id="facet-format" value={selectedFormat} onchange={(event) => debouncedFacetChange(event, 'fmt')}>
				<option value="">Tous</option>
				{#each optionList(formats, selectedFormat) as facet (facet.name)}
					<option value={facet.name}>{facet.name} ({facet.count})</option>
				{/each}
			</select>
		</label>

		<label class="select-field" for="facet-tag">
			<span>Categorie / tag</span>
			<select id="facet-tag" value={selectedTag} onchange={(event) => debouncedFacetChange(event, 'tag')}>
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
		<select id="sort" value={sort} onchange={(event) => debouncedSortChange(event)}>
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
