import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import Breadcrumb from '../../lib/ui/molecules/Breadcrumb.svelte';

describe('Breadcrumb', () => {
	it('affiche les items intermediaires comme liens et le dernier item comme page courante', () => {
		const view = render(Breadcrumb, {
			props: {
				ariaLabel: 'Fil de navigation test',
				items: [
					{ label: 'Recherche', href: '/' },
					{ label: 'Dataset mobilite', href: '/dataset/d1' },
					{ label: 'Ressource CSV' }
				]
			}
		});

		expect(view.body).toContain('Fil de navigation test');
		expect(view.body).toContain('href="/"');
		expect(view.body).toContain('href="/dataset/d1"');
		expect(view.body).toContain('aria-current="page"');
		expect(view.body).toContain('Ressource CSV');
	});

	it('n affiche rien quand la liste est vide', () => {
		const view = render(Breadcrumb, {
			props: {
				items: []
			}
		});

		expect(view.body).not.toContain('<nav');
	});
});
