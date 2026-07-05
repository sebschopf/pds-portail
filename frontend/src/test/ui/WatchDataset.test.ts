import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import WatchDataset from '../../lib/ui/molecules/WatchDataset.svelte';

describe('WatchDataset (surveillance de dataset)', () => {
	it('affiche le bouton de surveillance et la modale avec champ email', () => {
		const view = render(WatchDataset, {
			props: {
				dataset_id: 'mobilite-ch',
				dataset_title: 'Mobilité Suisse',
				polar_product_id: 'product_watch_monthly'
			}
		});

		// Bouton initial
		expect(view.body).toContain('Surveiller ce dataset');

		// Contenu modale
		expect(view.body).toContain('Surveillance de dataset');
		expect(view.body).toContain('5 CHF/mois');
		expect(view.body).toContain('Votre adresse email');
		expect(view.body).toContain('Procéder au paiement');
		expect(view.body).toContain('PDS-Portail ne stocke jamais vos données bancaires');
	});

	it('inclut les attributs ARIA pour l\'accessibilité WCAG AA', () => {
		const view = render(WatchDataset, {
			props: {
				dataset_id: 'dataset-1',
				dataset_title: 'Test Dataset',
				polar_product_id: 'product_test'
			}
		});

		expect(view.body).toContain('aria-modal="true"');
	});
});
