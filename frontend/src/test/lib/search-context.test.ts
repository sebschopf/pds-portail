import { describe, expect, it } from 'vitest';

import {
	appendSearchContext,
	buildSearchHref,
	normalizeSearchContext
} from '../../lib/navigation/search-context';

describe('search-context helpers', () => {
	it('normalise et filtre les cles de contexte autorisees', () => {
		expect(
			normalizeSearchContext('q=mobilite&sort=quality_desc&page=2&org=org-1&fmt=CSV&tag=transport&x=1')
		).toBe('q=mobilite&sort=quality_desc&page=2&org=org-1&fmt=CSV&tag=transport');
	});

	it('normalise le contexte multi-tags via tags=... et priorise ce format', () => {
		expect(
			normalizeSearchContext(
				'q=mobilite&sort=quality_desc&page=2&org=org-1&fmt=CSV&tags=transport,commune&tag=legacy'
			)
		).toBe('q=mobilite&sort=quality_desc&page=2&org=org-1&fmt=CSV&tags=transport%2Ccommune');
	});

	it('conserve les tags legacy repetes quand tags=... est absent', () => {
		expect(
			normalizeSearchContext('q=mobilite&tag=transport&tag=commune&tag=transport')
		).toBe('q=mobilite&tag=transport&tag=commune');
	});

	it('retourne null quand le contexte est vide ou invalide', () => {
		expect(normalizeSearchContext(null)).toBeNull();
		expect(normalizeSearchContext('page=0')).toBeNull();
	});

	it('construit un href de recherche avec fallback /', () => {
		expect(buildSearchHref('q=mobilite&page=2')).toBe('/?q=mobilite&page=2');
		expect(buildSearchHref('')).toBe('/');
	});

	it('annexe le contexte au chemin cible', () => {
		expect(appendSearchContext('/dataset/d1', 'q=mobilite&page=2')).toBe(
			'/dataset/d1?ctx=q%3Dmobilite%26page%3D2'
		);
		expect(appendSearchContext('/dataset/d1', null)).toBe('/dataset/d1');
	});
});