import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import Page from '../../routes/dataset/[id]/ponderation/+page.svelte';

describe('dataset/[id]/ponderation page', () => {
	it('affiche la formule du score et les 3 criteres avec explication et verification', () => {
		const view = render(Page, {
			props: {
				data: {
					datasetId: 'dataset-1'
				}
			}
		});

		expect(view.body).toContain('Comment le score de pertinence est calcule');
		expect(view.body).toContain("Les trois criteres qui determinent l'ordre des resultats");
		expect(view.body).toContain('Formule du score');
		expect(view.body).toContain('Score = 50% x Pertinence du texte + 30% x Qualite des donnees + 20% x Fraicheur');
		expect(view.body).toContain('Critere 1: Pertinence du texte (50%)');
		expect(view.body).toContain('Critere 2: Qualite des donnees (30%)');
		expect(view.body).toContain('Critere 3: Fraicheur des donnees (20%)');
		expect(view.body).toContain('Pourquoi ces pourcentages');
	});

	it('affiche les limites d interpretation et la navigation retour', () => {
		const view = render(Page, {
			props: {
				data: {
					datasetId: 'dataset-1'
				}
			}
		});

		expect(view.body).toContain("Limites d'interpretation");
		expect(view.body).toContain('ne garantit pas que les donnees sont exactes');
		expect(view.body).toContain('href="/dataset/dataset-1"');
		expect(view.body).toContain('Retour a la recherche');
		expect(view.body).toContain('aria-label="Fil de navigation ponderation"');
		expect(view.body).toContain('aria-label="Navigation ponderation"');
		expect(view.body).toContain('aria-labelledby="ranking-formula-title"');
		expect(view.body).toContain('aria-labelledby="ranking-text-title"');
		expect(view.body).toContain('aria-labelledby="ranking-quality-title"');
		expect(view.body).toContain('aria-labelledby="ranking-freshness-title"');
		expect(view.body).toContain('aria-labelledby="ranking-weights-title"');
		expect(view.body).toContain('aria-labelledby="ranking-limits-title"');
	});
});