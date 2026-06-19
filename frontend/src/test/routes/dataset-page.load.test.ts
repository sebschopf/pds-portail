import { describe, expect, it, vi } from 'vitest';

import { load } from '../../routes/dataset/[id]/+page';

describe('dataset/[id] load', () => {
	it('retourne un dataset conforme quand le backend repond 200', async () => {
		const data = await load({
			params: { id: 'dataset-1' },
			fetch: async () =>
				new Response(
					JSON.stringify({
						id: 'dataset-1',
						title: 'Dataset mobilite',
						description: 'Description',
						org_id: 'org-1',
						org_name: 'Office mobilite',
						license: 'CC-BY',
						quality_score: 85,
						completeness: 80,
						freshness_days: 12,
						resources: [
							{
								id: 'resource-1',
								name: 'Ressource 1',
								format: 'CSV',
								url: 'https://example.com/r1.csv',
								size_bytes: 1234,
								created: '2026-01-01',
								last_modified: '2026-01-05'
							}
						],
						dataset_structure: {
							fields: ['Nom', 'Prenom'],
							formats: ['CSV'],
							update_frequency: 'Annuelle',
							last_updated: '2026-01-15'
						}
					}),
					{ status: 200 }
				)
		} as never);

		expect(data.status).toBe('ok');
		expect(data.dataset?.title).toBe('Dataset mobilite');
		expect(data.dataset?.quality_score).toBe(85);
		expect(data.dataset?.completeness).toBe(80);
		expect(data.dataset?.freshness_days).toBe(12);
	});

	it('retourne not-found quand le backend repond 404', async () => {
		const data = await load({
			params: { id: 'inconnu' },
			fetch: async () => new Response(null, { status: 404 })
		} as never);

		expect(data.status).toBe('not-found');
	});

	it('retourne contract-error quand le payload ne respecte pas le contrat', async () => {
		const data = await load({
			params: { id: 'dataset-1' },
			fetch: async () =>
				new Response(
					JSON.stringify({
						id: 'dataset-1',
						title: 'Dataset incomplet'
					}),
					{ status: 200 }
				)
		} as never);

		expect(data.status).toBe('contract-error');
	});

	it('retourne error et message explicite pour une erreur API hors 404', async () => {
		const data = await load({
			params: { id: 'dataset-1' },
			fetch: async () => new Response(null, { status: 500 })
		} as never);

		expect(data.status).toBe('error');
		expect(data.datasetId).toBe('dataset-1');
		expect(data.errorMessage).toBe('Erreur API 500');
	});

	it('encode l identifiant dataset dans l URL backend', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
					id: 'dataset/avec espace',
					title: 'Dataset encode',
					description: null,
					org_id: null,
					org_name: null,
					license: null,
					quality_score: null,
					completeness: null,
					freshness_days: null,
					resources: [],
					dataset_structure: {
						fields: [],
						formats: [],
						update_frequency: null,
						last_updated: null
					}
				}),
				{ status: 200 }
			)
		);

		await load({
			params: { id: 'dataset/avec espace' },
			fetch: fetchMock
		} as never);

		expect(fetchMock).toHaveBeenCalledWith('/api/v1/dataset/dataset%2Favec%20espace');
	});

	it('recupere et normalise le contexte de recherche depuis l URL', async () => {
		const data = await load({
			params: { id: 'dataset-1' },
			url: new URL(
				'https://example.test/dataset/dataset-1?ctx=q%3Dmobi%26sort%3Dquality_desc%26page%3D2%26org%3Dorg-1%26fmt%3DCSV%26tag%3Dtransport'
			),
			fetch: async () =>
				new Response(
					JSON.stringify({
						id: 'dataset-1',
						title: 'Dataset mobilite',
						description: null,
						org_id: null,
						org_name: null,
						license: null,
						quality_score: null,
						completeness: null,
						freshness_days: null,
						resources: [],
						dataset_structure: {
							fields: [],
							formats: [],
							update_frequency: null,
							last_updated: null
						}
					}),
					{ status: 200 }
				)
		} as never);

		expect(data.searchContext).toBe(
			'q=mobi&sort=quality_desc&page=2&org=org-1&fmt=CSV&tag=transport'
		);
	});
});
