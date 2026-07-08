import { describe, expect, test, vi, beforeEach } from 'vitest';
import { flushSync } from 'svelte';
import { useSearch } from '$lib/runes/search.svelte';

// --- Mocks (factories utilent des fn() inline à cause du hoisting vi.mock) ---
vi.mock('$app/navigation', () => ({
	replaceState: vi.fn()
}));

vi.mock('$env/dynamic/public', () => ({
	env: {
		PUBLIC_USE_MOCK_API: '0',
		PUBLIC_API_BASE_URL: 'https://api.example.com'
	}
}));

vi.mock('$lib/navigation/search-context', () => ({
	normalizeSearchContext: (raw: string | null | undefined) => raw ?? null
}));

// --- Mock globals ---
globalThis.fetch = vi.fn();
globalThis.requestAnimationFrame = vi.fn((cb: (time: number) => void) => {
	cb(0);
	return 0;
});

// --- Mock window.location (utilise URL pour que URLSearchParams fonctionne) ---
const mockWindowLocation = {
	pathname: '/',
	search: '',
	href: 'http://localhost/'
} as Location;
globalThis.window = { location: mockWindowLocation } as unknown as Window & typeof globalThis;

// --- Récupérer les mocks hoistés ---
import { replaceState as mockReplaceState } from '$app/navigation';

// --- Helpers ---
function makeSearchResponse(
	overrides: Partial<{
		total: number;
		offset: number;
		limit: number;
		datasets: unknown[];
		facets: { organizations: unknown[]; formats: unknown[]; tags: unknown[] };
	}> = {}
) {
	return {
		total: 25,
		offset: 0,
		limit: 10,
		datasets: [
			{
				id: 'ds-1',
				title: 'Dataset 1',
				org_name: 'Org A',
				description: 'First dataset',
				quality_score: 80,
				completeness: 90,
				freshness_days: 10,
				resource_formats: ['CSV'],
				resource_count: 3,
				tags: ['env', 'climate']
			}
		],
		facets: {
			organizations: [{ name: 'Org A', count: 10, display_name: 'Org A' }],
			formats: [{ name: 'CSV', count: 5, display_name: 'CSV' }],
			tags: [{ name: 'env', count: 8, display_name: 'Environnement' }]
		},
		...overrides
	};
}

describe('useSearch', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockWindowLocation.pathname = '/';
		mockWindowLocation.search = '';
		mockWindowLocation.href = 'http://localhost/';
	});

	// --- État initial ---
	test('useSearch initialise avec les valeurs par défaut', () => {
		const search = useSearch();
		expect(search.query).toBe('');
		expect(search.sort).toBe('modified_desc');
		expect(search.selectedOrg).toBe('');
		expect(search.selectedFormat).toBe('');
		expect(search.selectedTags).toEqual([]);
		expect(search.currentPage).toBe(1);
		expect(search.isLoading).toBe(false);
		expect(search.errorMessage).toBe('');
		expect(search.data).toBeNull();
	});

	// --- Dérivés initiaux ---
	test('useSearch totalPages est 1 quand data est null', () => {
		const search = useSearch();
		expect(search.totalPages).toBe(1);
		expect(search.canGoPrev).toBe(false);
		expect(search.canGoNext).toBe(false);
	});

	test('useSearch activeFilterCount est 0 sans filtres', () => {
		const search = useSearch();
		expect(search.activeFilterCount).toBe(0);
	});

	test('useSearch compareDisabled est false quand compareIds < 4', () => {
		const search = useSearch();
		expect(search.compareDisabled).toBe(false);
	});

	test('useSearch readyState est success et readyLabel est Prêt à l’init', () => {
		const search = useSearch();
		flushSync();
		expect(search.readyState).toBe('success');
		expect(search.readyLabel).toBe('Prêt');
	});

	test('useSearch sortLabel retourne le label du tri par défaut', () => {
		const search = useSearch();
		flushSync();
		expect(search.sortLabel).toBe('Date (plus récent)');
	});

	// --- toggleCompare ---
	test('useSearch toggleCompare ajoute un dataset aux compareIds', () => {
		const search = useSearch();
		search.toggleCompare('ds-1');
		expect(search.compareIds).toEqual(['ds-1']);
	});

	test('useSearch toggleCompare retire un dataset déjà présent', () => {
		const search = useSearch();
		search.toggleCompare('ds-1');
		search.toggleCompare('ds-2');
		expect(search.compareIds).toEqual(['ds-1', 'ds-2']);

		search.toggleCompare('ds-1');
		expect(search.compareIds).toEqual(['ds-2']);
	});

	test('useSearch toggleCompare bloque au-delà de MAX_COMPARE=4', () => {
		const search = useSearch();
		search.toggleCompare('a');
		search.toggleCompare('b');
		search.toggleCompare('c');
		search.toggleCompare('d');
		expect(search.compareIds).toEqual(['a', 'b', 'c', 'd']);

		search.toggleCompare('e');
		expect(search.compareIds).toEqual(['a', 'b', 'c', 'd']);
		expect(search.compareDisabled).toBe(true);
	});

	test('useSearch clearCompare vide la liste', () => {
		const search = useSearch();
		search.toggleCompare('a');
		search.toggleCompare('b');
		expect(search.compareIds).toHaveLength(2);

		search.clearCompare();
		expect(search.compareIds).toEqual([]);
	});

	// --- navigateToCompare ---
	test('useSearch navigateToCompare redirige vers /comparer?ids=', () => {
		const savedLocation = window.location;
		const mockAssign = vi.fn();
		let _href = '';
		Object.defineProperty(globalThis.window, 'location', {
			value: {
				get href() {
					return _href;
				},
				set href(v: string) {
					_href = v;
					mockAssign(v);
				},
				pathname: '/',
				search: ''
			},
			writable: true,
			configurable: true
		});

		try {
			const search = useSearch();
			search.toggleCompare('ds-a');
			search.toggleCompare('ds-b');

			search.navigateToCompare();

			expect(mockAssign).toHaveBeenCalledWith('/comparer?ids=ds-a%2Cds-b');
		} finally {
			Object.defineProperty(globalThis.window, 'location', {
				value: savedLocation,
				writable: true
			});
		}
	});

	// --- runSearch: succès ---
	test('useSearch runSearch récupère les données et met à jour totalPages', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});
		const search = useSearch();

		await search.runSearch();

		expect(search.isLoading).toBe(false);
		expect(search.errorMessage).toBe('');
		expect(search.totalPages).toBe(3);
		expect(search.data).not.toBeNull();
		expect(search.data!.total).toBe(25);
		expect(search.organizations).toEqual([{ name: 'Org A', count: 10, display_name: 'Org A' }]);
		expect(search.formats).toEqual([{ name: 'CSV', count: 5, display_name: 'CSV' }]);
		expect(search.tags).toEqual([{ name: 'env', count: 8, display_name: 'Environnement' }]);
	});

	// --- runSearch: erreur ---
	test('useSearch runSearch définit errorMessage sur réponse non-ok', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ ok: false, status: 500 });
		const search = useSearch();

		await search.runSearch();

		expect(search.errorMessage).toBe('Erreur API 500');
		expect(search.data).toBeNull();
		expect(search.readyState).toBe('danger');
	});

	test('useSearch runSearch définit errorMessage sur échec réseau', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network Error'));
		const search = useSearch();

		await search.runSearch();

		expect(search.errorMessage).toBe('Network Error');
		expect(search.readyState).toBe('danger');
	});

	test('useSearch runSearch définit errorMessage générique pour erreur non-Error', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce('bizarre');
		const search = useSearch();

		await search.runSearch();

		expect(search.errorMessage).toBe('Erreur inconnue');
	});

	// --- readyState / readyLabel ---
	test('useSearch readyState est warning quand isLoading=true', () => {
		const search = useSearch();
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockReturnValueOnce(new Promise(() => {}));
		search.runSearch();

		expect(search.readyState).toBe('warning');
		expect(search.readyLabel).toBe('Recherche en cours…');
	});

	// --- submitSearch ---
	test('useSearch submitSearch réinitialise currentPage à 1 et lance la recherche', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse({ total: 5 }))
		});
		const search = useSearch();
		search.query = 'test';

		const fakeEvent = { preventDefault: vi.fn() } as unknown as SubmitEvent;
		await search.submitSearch(fakeEvent);

		expect(search.currentPage).toBe(1);
		expect(fakeEvent.preventDefault).toHaveBeenCalled();
		expect(search.totalPages).toBe(1);
	});

	// --- handleQueryChange ---
	test('useSearch handleQueryChange met à jour query et réinitialise la page', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});
		const search = useSearch();

		await search.handleQueryChange('nouvelle recherche');

		expect(search.query).toBe('nouvelle recherche');
		expect(search.currentPage).toBe(1);
	});

	// --- changeSort ---
	test('useSearch changeSort met à jour le tri et réinitialise la page', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});
		const search = useSearch();

		const fakeEvent = {
			currentTarget: { value: 'title_asc' }
		} as unknown as Event;
		await search.changeSort(fakeEvent);

		expect(search.sort).toBe('title_asc');
		expect(search.currentPage).toBe(1);
		flushSync();
		expect(search.sortLabel).toBe('Nom (A-Z)');
	});

	// --- changeFacet ---
	test('useSearch changeFacet met à jour selectedOrg pour facet=org', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});
		const search = useSearch();

		await search.changeFacet('Org A', 'org');

		expect(search.selectedOrg).toBe('Org A');
		expect(search.currentPage).toBe(1);
	});

	test('useSearch changeFacet met à jour selectedFormat pour facet=fmt', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});
		const search = useSearch();

		await search.changeFacet('CSV', 'fmt');

		expect(search.selectedFormat).toBe('CSV');
	});

	test('useSearch changeFacet met à jour selectedTags pour facet=tag avec un tableau', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});
		const search = useSearch();

		await search.changeFacet(['env', 'climate'], 'tag');

		expect(search.selectedTags).toEqual(['env', 'climate']);
		expect(search.activeFilterCount).toBe(2);
	});

	test('useSearch changeFacet met à jour selectedTags pour facet=tag avec une string unique', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});
		const search = useSearch();

		await search.changeFacet('env', 'tag');

		expect(search.selectedTags).toEqual(['env']);
	});

	// --- clearAllFilters ---
	test('useSearch clearAllFilters vide tous les filtres', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});
		const search = useSearch();
		search.selectedOrg = 'Org A';
		search.selectedFormat = 'CSV';
		search.selectedTags = ['env'];

		await search.clearAllFilters();

		expect(search.selectedOrg).toBe('');
		expect(search.selectedFormat).toBe('');
		expect(search.selectedTags).toEqual([]);
		expect(search.activeFilterCount).toBe(0);
		expect(search.currentPage).toBe(1);
	});

	// --- goToPage ---
	test('useSearch goToPage navigue vers la page demandée', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse({ total: 30 }))
		});
		const search = useSearch();
		await search.runSearch();

		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse({ total: 30, offset: 10 }))
		});
		await search.goToPage(2);

		expect(search.currentPage).toBe(2);
	});

	test('useSearch goToPage ignore page < 1', async () => {
		const search = useSearch();
		await search.goToPage(0);
		expect(globalThis.fetch).not.toHaveBeenCalled();
	});

	test('useSearch goToPage ignore page > totalPages', async () => {
		const search = useSearch();
		await search.goToPage(5);
		expect(globalThis.fetch).not.toHaveBeenCalled();
	});

	// --- init: hydrate l'état depuis l'URL puis lance la recherche ---
	test('useSearch init hydrate les paramètres de l’URL et lance runSearch', async () => {
		mockWindowLocation.search = '?q=test&sort=quality_desc&page=2&org=Org%20A&fmt=CSV&tags=env,climate';
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});

		const search = useSearch();
		await search.init();

		expect(search.query).toBe('test');
		expect(search.sort).toBe('quality_desc');
		expect(search.currentPage).toBe(2);
		expect(search.selectedOrg).toBe('Org A');
		expect(search.selectedFormat).toBe('CSV');
		expect(search.selectedTags).toEqual(['env', 'climate']);
	});

	test('useSearch init lit le tag simple quand pas de tags CSV', async () => {
		mockWindowLocation.search = '?tag=env';
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});

		const search = useSearch();
		await search.init();

		expect(search.selectedTags).toEqual(['env']);
	});

	test('useSearch init gère les tags legacy multiples via getAll(tag)', async () => {
		mockWindowLocation.search = '?tag=env&tag=climate';
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});

		const search = useSearch();
		await search.init();

		expect(search.selectedTags).toEqual(['env', 'climate']);
	});

	test('useSearch init ignore une page non numérique dans l’URL', async () => {
		mockWindowLocation.search = '?page=abc';
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});

		const search = useSearch();
		await search.init();

		expect(search.currentPage).toBe(1);
	});

	// --- buildSearchUrl ---
	test('useSearch buildSearchUrl construit l’URL avec le préfixe API', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});
		const search = useSearch();
		search.query = 'test';
		search.selectedOrg = 'Org A';
		search.selectedFormat = 'CSV';
		search.selectedTags = ['env'];

		await search.runSearch();

		const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string;
		expect(calledUrl).toContain('https://api.example.com/api/v1/search');
		expect(calledUrl).toContain('q=test');
		expect(calledUrl).toContain('org=Org+A');
		expect(calledUrl).toContain('fmt=CSV');
	});

	// --- syncUrlState appelle replaceState ---
	test('useSearch runSearch appelle replaceState pour synchroniser l’URL', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse())
		});
		const search = useSearch();
		search.query = 'hello';

		await search.runSearch();

		expect(mockReplaceState).toHaveBeenCalledWith(
			expect.stringContaining('/?q=hello'),
			expect.anything()
		);
	});

	// --- resultsKey ---
	test('useSearch resultsKey change avec les filtres', () => {
		const search = useSearch();
		flushSync();
		expect(search.resultsKey).toBe('|modified_desc||||1');

		search.query = 'test';
		flushSync();
		expect(search.resultsKey).toBe('test|modified_desc||||1');
	});

	// --- pageLabel ---
	test('useSearch pageLabel reflète la page courante', async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(makeSearchResponse({ total: 30 }))
		});
		const search = useSearch();
		await search.runSearch();
		flushSync();
		expect(search.pageLabel).toBe('Page 1/3');
	});

	// --- searchContext ---
	test('useSearch searchContext est dérivé des paramètres', () => {
		const search = useSearch();
		search.query = 'test';
		search.sort = 'hybrid';
		search.selectedOrg = 'Org A';
		search.selectedTags = ['env'];
		flushSync();

		expect(search.searchContext).toContain('q=test');
		expect(search.searchContext).toContain('sort=hybrid');
		expect(search.searchContext).toContain('org=Org+A');
		expect(search.searchContext).toContain('tag=env');
	});
});