import { describe, expect, it } from 'vitest';

import { getSafeExternalUrl } from '../../lib/security/external-url';

describe('external-url helper', () => {
	it('accepte les URLs http et https', () => {
		expect(getSafeExternalUrl('https://example.com/resource.csv')).toBe(
			'https://example.com/resource.csv'
		);
		expect(getSafeExternalUrl('http://example.com/resource.csv')).toBe(
			'http://example.com/resource.csv'
		);
	});

	it('rejette les schemas non autorises et les URLs invalides', () => {
		expect(getSafeExternalUrl('javascript:alert(1)')).toBeNull();
		expect(getSafeExternalUrl('data:text/plain,hello')).toBeNull();
		expect(getSafeExternalUrl('/relative/path')).toBeNull();
		expect(getSafeExternalUrl('')).toBeNull();
	});
});