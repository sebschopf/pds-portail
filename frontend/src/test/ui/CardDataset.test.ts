import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import CardDataset from '../../lib/ui/organisms/CardDataset.svelte';

const BASE_DATASET = {
	id: 'dataset-1',
	title: 'Dataset mobilite',
	org_name: 'Office mobilite',
	description: 'Donnees de mobilite urbaine',
	quality_score: 82,
	completeness: 88,
	freshness_days: 3,
	resource_formats: ['CSV', 'JSON'],
	resource_count: 2,
	tags: ['mobilite', 'transport']
};

const RANKING_SIGNALS_SAMPLE = {
	hybrid_score: 0.8512,
	text_score: 1.0,
	quality_normalized: 0.87,
	freshness_component: 0.9048,
	weight_text: 0.5,
	weight_quality: 0.3,
	weight_freshness: 0.2
};

describe('CardDataset', () => {
	it('affiche le lien vers la fiche dataset avec le bon href et aria-label discriminant', () => {
		const view = render(CardDataset, { props: { dataset: BASE_DATASET } });

		expect(view.body).toContain('href="/dataset/dataset-1"');
		expect(view.body).toContain('Ouvrir la fiche dataset');
		expect(view.body).toContain('aria-label="Ouvrir la fiche: Dataset mobilite"');
	});

	it('encode l identifiant dataset dans les liens de navigation et API', () => {
		const view = render(CardDataset, {
			props: {
				dataset: {
					...BASE_DATASET,
					id: 'dataset/avec espace'
				}
			}
		});

		expect(view.body).toContain('href="/dataset/dataset%2Favec%20espace"');
		expect(view.body).toContain('href="/api/v1/dataset/dataset%2Favec%20espace"');
	});

	it('preserve le contexte de recherche sur le lien dataset quand fourni', () => {
		const view = render(CardDataset, {
			props: {
				dataset: BASE_DATASET,
				searchContext: 'q=mobilite&sort=quality_desc&page=2&org=org-1&fmt=CSV&tag=transport'
			}
		});

		expect(view.body).toContain(
			'href="/dataset/dataset-1?ctx=q%3Dmobilite%26sort%3Dquality_desc%26page%3D2%26org%3Dorg-1%26fmt%3DCSV%26tag%3Dtransport"'
		);
	});

	it('affiche le fallback organisation quand org_name est null', () => {
		const view = render(CardDataset, {
			props: { dataset: { ...BASE_DATASET, org_name: null } }
		});

		expect(view.body).toContain('Non renseignée');
	});

	it('affiche le fallback description quand description est null', () => {
		const view = render(CardDataset, {
			props: { dataset: { ...BASE_DATASET, description: null } }
		});

		expect(view.body).toContain('Description non disponible.');
	});

	it('affiche le fallback format quand resource_formats est vide', () => {
		const view = render(CardDataset, {
			props: { dataset: { ...BASE_DATASET, resource_formats: [] } }
		});

		expect(view.body).toContain('Non renseigné');
	});

	it('affiche le fallback tags quand tags est vide', () => {
		const view = render(CardDataset, {
			props: { dataset: { ...BASE_DATASET, tags: [] } }
		});

		expect(view.body).toContain('Non renseignés');
	});

	it('affiche les metriques null avec le fallback Non renseigne', () => {
		const view = render(CardDataset, {
			props: {
				dataset: {
					...BASE_DATASET,
					quality_score: null,
					completeness: null,
					freshness_days: null
				}
			}
		});

		expect(view.body.match(/Non renseigné/g)?.length).toBeGreaterThanOrEqual(3);
	});

	it('tronque les tags au-dela de 5 avec une ellipse visuellement masquee et un libelle accessible', () => {
		const view = render(CardDataset, {
			props: {
				dataset: {
					...BASE_DATASET,
					tags: ['tag1', 'tag2', 'tag3', 'tag4', 'tag5', 'tag6']
				}
			}
		});

		expect(view.body).toContain('aria-hidden="true"');
		expect(view.body).toContain('et d\'autres tags');
		expect(view.body).not.toContain('tag6');
	});

	it('n affiche pas d ellipse quand le nombre de tags est inferieur ou egal a 5', () => {
		const view = render(CardDataset, {
			props: { dataset: { ...BASE_DATASET, tags: ['tag1', 'tag2', 'tag3'] } }
		});

		expect(view.body).not.toContain('...');
	});

	it('n affiche pas la section ranking quand ranking_signals est absent', () => {
		const view = render(CardDataset, {
			props: { dataset: BASE_DATASET }
		});

		expect(view.body).not.toContain('Score de pertinence');
		expect(view.body).not.toContain('Mots de la recherche');
	});

	it('affiche la section ranking avec le score hybride quand ranking_signals est fourni', () => {
		const view = render(CardDataset, {
			props: { dataset: { ...BASE_DATASET, ranking_signals: RANKING_SIGNALS_SAMPLE } }
		});

		expect(view.body).toContain('Score de pertinence');
		expect(view.body).toContain('85%');
	});

	it('affiche les raisons de classement triees par contribution decroissante', () => {
		const view = render(CardDataset, {
			props: { dataset: { ...BASE_DATASET, ranking_signals: RANKING_SIGNALS_SAMPLE } }
		});

		expect(view.body).toContain('Mots de la recherche dans le titre ou la description');
		expect(view.body).toContain('Qualité technique des métadonnées');
		expect(view.body).toContain('Fraîcheur des données');
	});

	it('affiche le lien vers la page ponderation quand ranking_signals est fourni', () => {
		const view = render(CardDataset, {
			props: { dataset: { ...BASE_DATASET, ranking_signals: RANKING_SIGNALS_SAMPLE } }
		});

		expect(view.body).toContain('Comprendre le calcul du score');
	});

	it('n affiche pas de raison pour une composante nulle', () => {
		const view = render(CardDataset, {
			props: {
				dataset: {
					...BASE_DATASET,
					ranking_signals: {
						...RANKING_SIGNALS_SAMPLE,
						text_score: 0,
						freshness_component: 0
					}
				}
			}
		});

		expect(view.body).not.toContain('Mots de la recherche');
		expect(view.body).not.toContain('Fraîcheur des données');
		expect(view.body).toContain('Qualité technique des métadonnées');
	});
});
