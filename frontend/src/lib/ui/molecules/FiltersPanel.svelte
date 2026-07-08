<script lang="ts">
	import Button from '../atoms/Button.svelte';
	import Input from '../atoms/Input.svelte';
	import SearchIcon from '../../assets/icons/SearchIcon.svelte';
	import FilterIcon from '../../assets/icons/FilterIcon.svelte';

	import type { FacetItem } from '$lib/types/search';

	let {
		query = $bindable(''),
		sort = $bindable('modified_desc'),
		selectedOrg = $bindable(''),
		selectedFormat = $bindable(''),
		selectedTags = $bindable([]),
		activeFilterCount = 0,
		organizations = [],
		formats = [],
		tags = [],
		sortOptions = [],
		onSubmit,
		onSortChange,
		onFacetChange,
		onQueryChange,
		onClearQuery,
		onClearFilters
	}: {
		query?: string;
		sort?: string;
		selectedOrg?: string;
		selectedFormat?: string;
		selectedTags?: string[];
		activeFilterCount?: number;
		organizations?: FacetItem[];
		formats?: FacetItem[];
		tags?: FacetItem[];
		sortOptions?: Array<{ value: string; label: string }>;
		onSubmit: (event: SubmitEvent) => Promise<void> | void;
		onSortChange: (event: Event) => Promise<void> | void;
		onFacetChange: (
			value: string | string[],
			facet: 'org' | 'fmt' | 'tag'
		) => Promise<void> | void;
		onQueryChange: (value: string) => Promise<void> | void;
		onClearQuery: () => Promise<void> | void;
		onClearFilters: () => Promise<void> | void;
	} = $props();

	/**
	 * Met a jour immediatement la variable bindable ET notifie le parent.
	 * Chaque facette a son propre timer pour permettre les changements rapides
	 * sans perdre de selection (ex: changer Org puis Format avant debounce).
	 */
	const facetTimers: Record<string, ReturnType<typeof setTimeout> | null> = {};

	function immediateFacetChange(event: Event, facet: 'org' | 'fmt'): void {
		const target = event.currentTarget as HTMLSelectElement;
		const value = target.value;

		// Mise a jour immediate de la variable bindable locale
		if (facet === 'org') selectedOrg = value;
		if (facet === 'fmt') selectedFormat = value;

		// Debounce independant par facette pour eviter les appels API en rafale
		if (facetTimers[facet]) clearTimeout(facetTimers[facet]!);
		facetTimers[facet] = setTimeout(() => {
			onFacetChange(value, facet);
		}, 300);
	}

	function immediateTagFacetChange(event: Event): void {
		const target = event.currentTarget as HTMLSelectElement;
		const values = Array.from(target.selectedOptions)
			.map((option) => option.value)
			.filter((value) => value.length > 0);

		selectedTags = values;

		if (facetTimers.tag) clearTimeout(facetTimers.tag);
		facetTimers.tag = setTimeout(() => {
			onFacetChange(values, 'tag');
		}, 300);
	}

	function toggleTagOption(event: MouseEvent): void {
		const option = event.target;
		if (!(option instanceof HTMLOptionElement)) {
			return;
		}

		// Permet une multi-selection au clic simple sans exiger Ctrl/Cmd.
		event.preventDefault();
		option.selected = !option.selected;
		const select = event.currentTarget as HTMLSelectElement;
		select.focus();

		const values = Array.from(select.selectedOptions)
			.map((selectedOption) => selectedOption.value)
			.filter((value) => value.length > 0);
		selectedTags = values;

		if (facetTimers.tag) clearTimeout(facetTimers.tag);
		facetTimers.tag = setTimeout(() => {
			onFacetChange(values, 'tag');
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

	// Debounce pour le champ texte : declenche la recherche automatiquement
	// apres l'arret de la frappe (comportement type recherche instantanee)
	const queryTimer: { current: ReturnType<typeof setTimeout> | null } = { current: null };

	function handleQueryInput(event: Event): void {
		const target = event.currentTarget as HTMLInputElement;
		const value = target.value;
		query = value;

		if (queryTimer.current) clearTimeout(queryTimer.current);
		queryTimer.current = setTimeout(() => {
			onQueryChange(value);
		}, 400);
	}

	function optionList(items: FacetItem[], selectedValue: string): FacetItem[] {
		// Dedoublonne par nom pour eviter each_key_duplicate
		const seen: string[] = [];
		const deduped = items.filter((item) => {
			if (seen.includes(item.name)) return false;
			seen.push(item.name);
			return true;
		});

		if (!selectedValue || seen.includes(selectedValue)) {
			return deduped;
		}
		return [{ name: selectedValue, count: 0, display_name: selectedValue }, ...deduped];
	}

	function optionListMultiple(items: FacetItem[], selectedValues: string[]): FacetItem[] {
		const seen: string[] = [];
		const deduped = items.filter((item) => {
			if (seen.includes(item.name)) return false;
			seen.push(item.name);
			return true;
		});

		const missing = selectedValues
			.filter((value) => !seen.includes(value))
			.map((value) => ({ name: value, count: 0, display_name: value }));

		return [...missing, ...deduped];
	}
</script>

<form class="search" onsubmit={onSubmit}>
	<label class="search-field" for="q">
		<span class="search-label">Rechercher</span>
		<div class="search-input-wrap">
			<input
				id="q"
				type="text"
				bind:value={query}
				oninput={handleQueryInput}
				placeholder="ex: mobilite, geographie"
			/>
			<span class="search-icon" aria-hidden="true">
				<SearchIcon size="var(--icon-size-md)" label="Rechercher" />
			</span>
		</div>
	</label>

	<fieldset class="facets-toolbar">
		<legend class="facets-legend">
			<FilterIcon size="var(--icon-size-md)" label="Filtrer" />
			Filtres facettes
		</legend>
		<label class="select-field" for="facet-org">
			<span>Organisation</span>
			<select id="facet-org" value={selectedOrg} onchange={(event) => immediateFacetChange(event, 'org')}>
				<option value="">Toutes</option>
				{#each optionList(organizations, selectedOrg) as facet, idx (`org-${facet.name}-${idx}`)}
					<option value={facet.name}>{facet.display_name ?? facet.name} ({facet.count})</option>
				{/each}
			</select>
		</label>

		<label class="select-field" for="facet-format">
			<span>Format</span>
			<select id="facet-format" value={selectedFormat} onchange={(event) => immediateFacetChange(event, 'fmt')}>
				<option value="">Tous</option>
				{#each optionList(formats, selectedFormat) as facet, idx (`fmt-${facet.name}-${idx}`)}
					<option value={facet.name}>{facet.name} ({facet.count})</option>
				{/each}
			</select>
		</label>

		<label class="select-field" for="facet-tag">
			<span>Categorie / tag</span>
			<small class="select-help">Clic simple pour ajouter ou retirer un tag.</small>
			<select
				id="facet-tag"
				class="tag-select"
				multiple
				size="6"
				bind:value={selectedTags}
				onmousedown={toggleTagOption}
				onchange={immediateTagFacetChange}
			>
				{#each optionListMultiple(tags, selectedTags) as facet, idx (`tag-${facet.name}-${idx}`)}
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

	.search-field {
		display: grid;
		gap: var(--space-2);
		font-size: var(--font-size-ui);
	}

	.search-label {
		font-weight: 600;
		color: var(--color-on-surface-subtle);
	}

	.search-input-wrap {
		position: relative;
		display: flex;
		align-items: center;
	}

	.search-input-wrap input {
		border: var(--border-thin) solid var(--color-border);
		background: var(--color-surface);
		border-radius: var(--radius-none);
		padding: var(--space-3) var(--space-7) var(--space-3) var(--space-4);
		min-height: var(--size-control-md);
		color: var(--color-on-surface);
		width: 100%;
		font-size: var(--font-size-ui);
	}

	.search-input-wrap input:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	.search-icon {
		position: absolute;
		right: var(--space-3);
		top: 50%;
		transform: translateY(-50%);
		color: var(--color-on-surface-subtle);
		pointer-events: none;
		display: flex;
		align-items: center;
	}

	.facets-toolbar {
		display: grid;
		gap: var(--space-3);
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		margin: 0;
		padding: 0;
		border: 0;
	}

	.facets-legend {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-weight: 700;
		font-size: var(--font-size-ui);
		margin-bottom: var(--space-1);
		color: var(--color-on-surface-soft);
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

	.select-help {
		font-size: var(--font-size-caption);
		color: var(--color-on-surface-subtle);
	}

	.select-field select {
		border: var(--border-thin) solid var(--color-border);
		background: var(--color-surface);
		border-radius: var(--radius-none);
		padding: var(--space-3) var(--space-4);
		min-height: var(--size-control-md);
		color: var(--color-on-surface);
		width: 100%;
		max-width: 100%;
	}

	.select-field select:not([multiple]) {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.tag-select {
		min-height: calc(var(--size-control-md) * 2.75);
		overflow-y: auto;
		white-space: normal;
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
