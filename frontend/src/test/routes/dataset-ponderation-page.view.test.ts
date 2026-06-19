import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import Page from '../../routes/dataset/[id]/ponderation/+page.svelte';

describe('dataset/[id]/ponderation page', () => {
	it('affiche la formule et les 5 composantes avec calcul et verification', () => {
		const view = render(Page, {
			props: {
				data: {
					datasetId: 'dataset-1'
				}
			}
		});

		expect(view.body).toContain('Ponderation du score qualite');
		expect(view.body).toContain('Formule du score');
		expect(view.body).toContain('Score = 20 x (Completude + Fraicheur + Formats standards + Signal geo-temporel + Nombre de');
		expect(view.body).toContain('Chaque composante vaut 0, 0.5 ou 1');
		expect(view.body).toContain('Composante 1 - Completude');
		expect(view.body).toContain('Composante 2 - Fraicheur');
		expect(view.body).toContain('Composante 3 - Formats standards');
		expect(view.body).toContain('Composante 4 - Signal geo-temporel');
		expect(view.body).toContain('Composante 5 - Nombre de ressources');
		expect(view.body).toContain('Comment c est calcule');
		expect(view.body).toContain('Comment je peux verifier');
	});

	it('affiche les limites d interpretation et la navigation retour', () => {
		const view = render(Page, {
			props: {
				data: {
					datasetId: 'dataset-1'
				}
			}
		});

		expect(view.body).toContain('Limites d interpretation');
		expect(view.body).toMatch(/Il ne prouve pas que les donnees sont\s+vraies/);
		expect(view.body).toContain('href="/dataset/dataset-1"');
		expect(view.body).toContain('Retour a la recherche');
		expect(view.body).toContain('aria-label="Fil de navigation ponderation"');
		expect(view.body).toContain('aria-label="Navigation ponderation"');
		expect(view.body).toContain('aria-labelledby="ponderation-formula-title"');
		expect(view.body).toContain('aria-labelledby="ponderation-completeness-title"');
		expect(view.body).toContain('aria-labelledby="ponderation-freshness-title"');
		expect(view.body).toContain('aria-labelledby="ponderation-formats-title"');
		expect(view.body).toContain('aria-labelledby="ponderation-signal-title"');
		expect(view.body).toContain('aria-labelledby="ponderation-resources-title"');
		expect(view.body).toContain('aria-labelledby="ponderation-limits-title"');
	});
});