import { describe, expect, it } from 'vitest';
import { buildSearchRecords, MOCK_DATASETS } from '../../lib/mock/mock-api-data';

/**
 * Tests unitaires pour la logique de filtrage/recherche du mock API.
 *
 * NB: Ces tests exercent directement buildSearchRecords et la logique de
 * filtrage (org, format, tag, texte) implementee dans
 * le handler GET /api/v1/search/+server.ts.
 */

function parseQueryTerms(rawQuery: string): string[] {
	const terms: string[] = [];
	const matcher = /"([^"]+)"|(\S+)/g;
	let match: RegExpExecArray | null = matcher.exec(rawQuery.toLowerCase());
	while (match) {
		terms.push((match[1] || match[2]).toLowerCase());
		match = matcher.exec(rawQuery.toLowerCase());
	}
	return terms;
}

interface SearchRecord {
	id: string;
	title: string;
	org_id?: string;
	org_name: string | null;
	description: string | null;
	resource_formats: string[];
	tags: string[];
	[key: string]: unknown;
}

function filterRecords(
	records: SearchRecord[],
	opts: { query?: string; org?: string; format?: string; tag?: string }
): SearchRecord[] {
	const terms = opts.query ? parseQueryTerms(opts.query) : [];

	return records.filter((dataset) => {
		if (opts.org && dataset.org_id !== opts.org && dataset.org_name !== opts.org) {
			return false;
		}
		if (
			opts.format &&
			!dataset.resource_formats.some(
				(fmt) => fmt.toUpperCase() === opts.format!.toUpperCase()
			)
		) {
			return false;
		}
		if (
			opts.tag &&
			!dataset.tags.some(
				(t) => t.toUpperCase() === opts.tag!.toUpperCase()
			)
		) {
			return false;
		}
		if (terms.length === 0) return true;

		const haystack = [
			dataset.title,
			dataset.description ?? '',
			dataset.org_name ?? '',
			dataset.tags.join(' '),
			dataset.resource_formats.join(' ')
		]
			.join(' ')
			.toLowerCase();

		return terms.every((term) => haystack.includes(term));
	});
}

const mockRecords: SearchRecord[] = buildSearchRecords([]) as SearchRecord[];

describe('Logique de filtrage mock API (search)', () => {
	it('retourne tous les datasets sans filtre', () => {
		const results = filterRecords(mockRecords, {});
		expect(results).toHaveLength(MOCK_DATASETS.length);
	});

	it('filtre par texte "mobilite"', () => {
		const results = filterRecords(mockRecords, { query: 'mobilite' });
		expect(results).toHaveLength(1);
		expect(results[0].title).toBe('Mobilite communale 2026');
	});

	it('filtre par organisation avec org_id exact', () => {
		const results = filterRecords(mockRecords, { org: 'org-mobilite' });
		expect(results).toHaveLength(1);
		expect(results[0].org_id).toBe('org-mobilite');
	});

	it('filtre par organisation avec org_name exact', () => {
		const results = filterRecords(mockRecords, { org: 'Office mobilite' });
		expect(results).toHaveLength(1);
		expect(results[0].org_name).toBe('Office mobilite');
	});

	it('filtre par format (insensible a la casse)', () => {
		const results = filterRecords(mockRecords, { format: 'csv' });
		expect(results).toHaveLength(1);
		expect(results[0].resource_formats).toContain('CSV');
	});

	it('filtre par format avec casse exacte', () => {
		const results = filterRecords(mockRecords, { format: 'CSV' });
		expect(results).toHaveLength(1);
	});

	it('filtre par tag exact (insensible a la casse)', () => {
		const results = filterRecords(mockRecords, { tag: 'transport' });
		expect(results).toHaveLength(1);
		expect(results[0].tags).toContain('transport');
	});

	it('filtre par tag avec casse differente', () => {
		const results = filterRecords(mockRecords, { tag: 'TRANSPORT' });
		expect(results).toHaveLength(1);
		expect(results[0].tags).toContain('transport');
	});

	it('combine texte + org + format + tag : donne un resultat', () => {
		const results = filterRecords(mockRecords, {
			query: 'mobilite',
			org: 'org-mobilite',
			format: 'CSV',
			tag: 'transport'
		});
		expect(results).toHaveLength(1);
	});

	it('combine tous les filtres : zero si combinaison impossible', () => {
		const results = filterRecords(mockRecords, {
			query: 'mobilite',
			org: 'org-mobilite',
			format: 'XLSX',
			tag: 'transport'
		});
		expect(results).toHaveLength(0);
	});

	it('enlever un filtre fait reapparaitre les resultats', () => {
		const zero = filterRecords(mockRecords, {
			query: 'mobilite', org: 'org-mobilite',
			format: 'XLSX', tag: 'transport'
		});
		expect(zero).toHaveLength(0);

		const back = filterRecords(mockRecords, {
			query: 'mobilite', org: 'org-mobilite',
			tag: 'transport'
		});
		expect(back).toHaveLength(1);
	});

	it('filtre par tag seul sans query texte', () => {
		const results = filterRecords(mockRecords, { tag: 'demographie' });
		expect(results).toHaveLength(1);
		expect(results[0].title).toBe('Population cantonale');
	});

	it('filtres cumules org + format sans query texte', () => {
		const results = filterRecords(mockRecords, {
			org: 'org-mobilite', format: 'JSON'
		});
		expect(results).toHaveLength(1);
		expect(results[0].resource_formats).toContain('JSON');
	});

	it('filtres cumules org + tag sans query texte', () => {
		const results = filterRecords(mockRecords, {
			org: 'org-mobilite', tag: 'commune'
		});
		expect(results).toHaveLength(1);
	});

	it('aucun filtre ne correspond -> liste vide', () => {
		const results = filterRecords(mockRecords, { tag: 'inexistant' });
		expect(results).toHaveLength(0);
	});

	it('les facettes contiennent les bons compteurs', () => {
		const filtered = filterRecords(mockRecords, { query: 'mobilite' });
		expect(filtered).toHaveLength(1);

		const orgs = new Set<string>();
		const formats = new Set<string>();
		const tags = new Set<string>();
		for (const ds of filtered) {
			if (ds.org_name) orgs.add(ds.org_id ?? ds.id);
			for (const f of ds.resource_formats) formats.add(f);
			for (const t of ds.tags) tags.add(t);
		}

		expect(orgs.has('org-mobilite')).toBe(true);
		expect(formats.has('CSV')).toBe(true);
		expect(formats.has('JSON')).toBe(true);
		expect(tags.has('transport')).toBe(true);
	});
});
