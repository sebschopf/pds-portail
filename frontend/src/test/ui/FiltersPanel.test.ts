import { describe, expect, it, vi } from 'vitest';
import { render } from 'svelte/server';

import FiltersPanel from '../../lib/ui/FiltersPanel.svelte';

describe('FiltersPanel', () => {
	it('affiche les options de tri et facettes attendues', () => {
		const view = render(FiltersPanel, {
			props: {
				query: 'mobilite',
				sort: 'quality_desc',
				selectedOrg: 'org-1',
				selectedFormat: 'CSV',
				selectedTag: 'transport',
				activeFilterCount: 3,
				organizations: [{ name: 'org-1', count: 2, display_name: 'Office mobilite' }],
				formats: [{ name: 'CSV', count: 4 }],
				tags: [{ name: 'transport', count: 3 }],
				sortOptions: [
					{ value: 'modified_desc', label: 'Date (plus recent)' },
					{ value: 'quality_desc', label: 'Qualite (meilleure)' }
				],
				onSubmit: vi.fn(),
				onSortChange: vi.fn(),
				onFacetChange: vi.fn(),
				onClearQuery: vi.fn(),
				onClearFilters: vi.fn()
			}
		});

		expect(view.body).toContain('Filtres actifs: 3');
		expect(view.body).toContain('Office mobilite');
		expect(view.body).toContain('Qualite (meilleure)');
		expect(view.body).toContain('Vider les filtres');
	});

	it('injecte une option fallback quand une valeur selectionnee est absente des facettes', () => {
		const view = render(FiltersPanel, {
			props: {
				selectedOrg: 'org-disparu',
				activeFilterCount: 1,
				organizations: [],
				formats: [],
				tags: [],
				sortOptions: [{ value: 'modified_desc', label: 'Date (plus recent)' }],
				onSubmit: vi.fn(),
				onSortChange: vi.fn(),
				onFacetChange: vi.fn(),
				onClearQuery: vi.fn(),
				onClearFilters: vi.fn()
			}
		});

		expect(view.body).toContain('org-disparu');
	});
});
