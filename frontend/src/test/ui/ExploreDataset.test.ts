import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import ExploreDataset from '../../lib/ui/organisms/ExploreDataset.svelte';

describe('ExploreDataset', () => {
	it('affiche l etat verrouille avec formulaire de cle API', () => {
		const view = render(ExploreDataset, {
			props: {
				resourceId: 'resource-123'
			}
		});

		expect(view.body).toContain('Exploration des champs');
		expect(view.body).toContain('Saisissez votre clé d\'accès premium');
		expect(view.body).toContain('Clé API premium');
		expect(view.body).toContain('placeholder="Ex: pds_live_xxxxx"');
		expect(view.body).toContain('Debloquer l\'exploration');
		expect(view.body).toContain('aria-label="Exploration des champs"');
		expect(view.body).toContain('id="explore-key-resource-123"');
	});

	it('n affiche pas les resultats ni les erreurs au rendu initial', () => {
		const view = render(ExploreDataset, {
			props: {
				resourceId: 'resource-abc'
			}
		});

		expect(view.body).not.toContain('Colonnes detectees pour la ressource');
		expect(view.body).not.toContain('Cartes resume statistiques');
		expect(view.body).not.toContain('role="alert"');
		expect(view.body).not.toContain('Analyse du fichier en cours...');
	});
});
