import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import Page from '../../routes/dataset/[id]/ponderation/+page.svelte';

describe('dataset/[id]/ponderation page', () => {
	it('affiche la formule du score hybride et les 3 composantes avec calcul et verification', () => {
		const view = render(Page, {
			props: {
				data: {
					datasetId: 'dataset-1'
				}
			}
		});

		expect(view.body).toContain('Comment le score de pertinence est calcule');
		expect(view.body).toContain('Score hybride combinant texte, qualite et fraicheur (PDS-40)');
		expect(view.body).toContain('Formule du score hybride');
		expect(view.body).toContain('Score = 50% x Pertinence texte + 30% x Qualite normalisee + 20% x Fraicheur');
		expect(view.body).toContain('Composante 1 — Pertinence texte (50%)');
		expect(view.body).toContain('Composante 2 — Qualite technique (30%)');
		expect(view.body).toContain('Composante 3 — Fraicheur des donnees (20%)');
		expect(view.body).toContain('Pourquoi ces poids');
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
		expect(view.body).toContain('ne garantit pas que les donnees sont vraies');
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