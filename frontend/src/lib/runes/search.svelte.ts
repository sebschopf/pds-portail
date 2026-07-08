import { env } from '$env/dynamic/public';
import { replaceState } from '$app/navigation';
import { normalizeSearchContext } from '$lib/navigation/search-context';
import type { SearchResponse } from '$lib/types/search';

export type SortValue =
	| 'modified_desc'
	| 'modified_asc'
	| 'quality_desc'
	| 'quality_asc'
	| 'hybrid'
	| 'title_asc'
	| 'title_desc';

const PAGE_SIZE = 10;
const MAX_COMPARE = 4;

export const sortLabels: Record<SortValue, string> = {
	modified_desc: 'Date (plus récent)',
	modified_asc: 'Date (plus ancien)',
	quality_desc: 'Qualité (meilleure)',
	quality_asc: 'Qualité (moins bonne)',
	hybrid: 'Pertinence (hybride)',
	title_asc: 'Nom (A-Z)',
	title_desc: 'Nom (Z-A)'
};

export const sortOptions = Object.entries(sortLabels).map(([value, label]) => ({ value, label }));

/**
 * Rune de recherche — encapsule tout l'état et la logique de la page d'accueil.
 *
 * Usage :
 *   const search = useSearch();
 *   onMount(() => search.init());
 */
export function useSearch() {
	let query = $state('');
	let sort = $state<SortValue>('modified_desc');
	let selectedOrg = $state('');
	let selectedFormat = $state('');
	let selectedTags = $state<string[]>([]);
	let currentPage = $state(1);
	let isLoading = $state(false);
	let errorMessage = $state('');
	let data = $state<SearchResponse | null>(null);

	// État comparaison guidée (PDS-43)
	let compareIds = $state<string[]>([]);

	// Dérivés
	const compareDisabled = $derived(compareIds.length >= MAX_COMPARE);
	const totalPages = $derived.by(() => {
		if (!data) return 1;
		return Math.max(1, Math.ceil(data.total / data.limit));
	});
	const canGoPrev = $derived(currentPage > 1);
	const canGoNext = $derived(currentPage < totalPages);
	const activeFilterCount = $derived(
		(selectedOrg ? 1 : 0) + (selectedFormat ? 1 : 0) + selectedTags.length
	);
	const readyState = $derived(errorMessage ? 'danger' : isLoading ? 'warning' : 'success');
	const readyLabel = $derived(errorMessage ? 'Erreur' : isLoading ? 'Recherche en cours…' : 'Prêt');
	const sortLabel = $derived(sortLabels[sort] ?? 'Tri');
	const pageLabel = $derived(`Page ${currentPage}/${totalPages}`);
	const organizations = $derived.by(() => data?.facets?.organizations ?? []);
	const formats = $derived.by(() => data?.facets?.formats ?? []);
	const tags = $derived.by(() => data?.facets?.tags ?? []);

	const useMockApi = env.PUBLIC_USE_MOCK_API === '1';
	const apiBase = useMockApi ? '' : (env.PUBLIC_API_BASE_URL || '');
	const searchContext = $derived.by(() => normalizeSearchContext(buildSearchStateParams().toString()));
	const resultsKey = $derived(
		`${query}|${sort}|${selectedOrg}|${selectedFormat}|${selectedTags.join(',')}|${currentPage}`
	);

	// --- Helpers ---
	function dedupe(values: string[]): string[] {
		const output: string[] = [];
		for (const value of values) {
			if (!output.includes(value)) {
				output.push(value);
			}
		}
		return output;
	}

	function parseSelectedTags(params: URLSearchParams): string[] {
		const csvTags = (params.get('tags') ?? '')
			.split(',')
			.map((tag) => tag.trim())
			.filter((tag) => tag.length > 0);
		if (csvTags.length > 0) return dedupe(csvTags);

		const legacyTags = params
			.getAll('tag')
			.map((tag) => tag.trim())
			.filter((tag) => tag.length > 0);
		if (legacyTags.length > 0) return dedupe(legacyTags);

		const singleLegacyTag = (params.get('tag') ?? '').trim();
		return singleLegacyTag.length > 0 ? [singleLegacyTag] : [];
	}

	function safeTrim(value: string): string {
		return value.trim();
	}

	function buildSearchStateParams(): URLSearchParams {
		const params = new URLSearchParams();
		const textQuery = safeTrim(query);
		if (textQuery.length > 0) params.set('q', textQuery);
		if (sort !== 'modified_desc') params.set('sort', sort);
		if (currentPage > 1) params.set('page', String(currentPage));
		if (selectedOrg) params.set('org', selectedOrg);
		if (selectedFormat) params.set('fmt', selectedFormat);
		if (selectedTags.length === 1) params.set('tag', selectedTags[0]);
		if (selectedTags.length > 1) params.set('tags', selectedTags.join(','));
		return params;
	}

	function syncUrlState(): void {
		const params = buildSearchStateParams();
		const queryString = params.toString();
		const nextUrl = queryString.length > 0 ? `${window.location.pathname}?${queryString}` : window.location.pathname;
		replaceState(nextUrl, {});
	}

	function buildSearchUrl(): string {
		const params = new URLSearchParams({
			offset: String((currentPage - 1) * PAGE_SIZE),
			limit: String(PAGE_SIZE),
			sort
		});
		const textQuery = safeTrim(query);
		if (textQuery.length > 0) params.set('q', textQuery);
		if (selectedOrg) params.set('org', selectedOrg);
		if (selectedFormat) params.set('fmt', selectedFormat);
		for (const tag of selectedTags) params.append('tag', tag);
		if (selectedTags.length > 1) params.set('tags', selectedTags.join(','));
		return `${apiBase}/api/v1/search?${params.toString()}`;
	}

	// --- Actions ---
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

	async function runSearch({
		focusResults = false,
		resultHeading
	}: { focusResults?: boolean; resultHeading?: HTMLElement | null } = {}): Promise<void> {
		isLoading = true;
		errorMessage = '';
		try {
			const response = await fetch(buildSearchUrl());
			if (!response.ok) throw new Error(`Erreur API ${response.status}`);
			data = (await response.json()) as SearchResponse;
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
			data = null;
		} finally {
			syncUrlState();
			isLoading = false;
			if (focusResults && resultHeading) {
				requestAnimationFrame(() => resultHeading.focus());
			}
		}
	}

	async function submitSearch(event: SubmitEvent, resultHeading?: HTMLElement | null): Promise<void> {
		event.preventDefault();
		currentPage = 1;
		await runSearch({ focusResults: true, resultHeading });
	}

	async function handleQueryChange(newQuery: string, resultHeading?: HTMLElement | null): Promise<void> {
		query = newQuery;
		currentPage = 1;
		await runSearch({ focusResults: true, resultHeading });
	}

	async function changeSort(event: Event): Promise<void> {
		sort = (event.currentTarget as HTMLSelectElement).value as SortValue;
		currentPage = 1;
		await runSearch();
	}

	async function changeFacet(
		value: string | string[],
		facet: 'org' | 'fmt' | 'tag'
	): Promise<void> {
		if (facet === 'org') selectedOrg = value as string;
		if (facet === 'fmt') selectedFormat = value as string;
		if (facet === 'tag') selectedTags = Array.isArray(value) ? value : value ? [value] : [];
		currentPage = 1;
		await runSearch();
	}

	async function clearAllFilters(): Promise<void> {
		selectedOrg = '';
		selectedFormat = '';
		selectedTags = [];
		currentPage = 1;
		await runSearch();
	}

	async function goToPage(page: number, resultHeading?: HTMLElement | null): Promise<void> {
		if (page < 1 || page > totalPages) return;
		currentPage = page;
		await runSearch({ focusResults: true, resultHeading });
	}

	function hydrateStateFromUrl(): void {
		const params = new URLSearchParams(window.location.search);
		const urlSort = params.get('sort');
		const urlPage = params.get('page');

		query = params.get('q') ?? '';
		selectedOrg = params.get('org') ?? '';
		selectedFormat = params.get('fmt') ?? '';
		selectedTags = parseSelectedTags(params);

		if (urlSort && urlSort in sortLabels) sort = urlSort as SortValue;

		if (urlPage) {
			const parsed = Number.parseInt(urlPage, 10);
			if (Number.isFinite(parsed) && parsed > 0) currentPage = parsed;
		}
	}

	async function init(resultHeading?: HTMLElement | null): Promise<void> {
		hydrateStateFromUrl();
		await runSearch({ resultHeading });
	}

	return {
		// State (read-only via getters)
		get query() {
			return query;
		},
		set query(v: string) {
			query = v;
		},
		get sort() {
			return sort;
		},
		set sort(v: SortValue) {
			sort = v;
		},
		get selectedOrg() {
			return selectedOrg;
		},
		set selectedOrg(v: string) {
			selectedOrg = v;
		},
		get selectedFormat() {
			return selectedFormat;
		},
		set selectedFormat(v: string) {
			selectedFormat = v;
		},
		get selectedTags() {
			return selectedTags;
		},
		set selectedTags(v: string[]) {
			selectedTags = v;
		},
		get currentPage() {
			return currentPage;
		},
		get isLoading() {
			return isLoading;
		},
		get errorMessage() {
			return errorMessage;
		},
		get data() {
			return data;
		},
		get compareIds() {
			return compareIds;
		},
		// Derived
		get compareDisabled() {
			return compareDisabled;
		},
		get totalPages() {
			return totalPages;
		},
		get canGoPrev() {
			return canGoPrev;
		},
		get canGoNext() {
			return canGoNext;
		},
		get activeFilterCount() {
			return activeFilterCount;
		},
		get readyState() {
			return readyState;
		},
		get readyLabel() {
			return readyLabel;
		},
		get sortLabel() {
			return sortLabel;
		},
		get pageLabel() {
			return pageLabel;
		},
		get organizations() {
			return organizations;
		},
		get formats() {
			return formats;
		},
		get tags() {
			return tags;
		},
		get searchContext() {
			return searchContext;
		},
		get resultsKey() {
			return resultsKey;
		},
		// Actions
		toggleCompare,
		clearCompare,
		navigateToCompare,
		runSearch,
		submitSearch,
		handleQueryChange,
		changeSort,
		changeFacet,
		clearAllFilters,
		goToPage,
		init
	};
}