import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import Page from '../../routes/resource/[id]/+page.svelte';

describe('resource/[id] page', () => {
	const defaultResource = {
		id: 'resource-1',
		name: 'Ressource mobilite communale',
		format: 'CSV',
		url: 'https://example.com/files/resource-1.csv',
		size_bytes: 27891,
		created: '2026-01-01',
		last_modified: '2026-01-10',
		dataset_id: 'dataset-1',
		dataset_title: 'Dataset mobilite'
	};

	it('affiche les informations ressource et les liens de navigation', () => {
		const view = render(Page, {
			props: {
				data: {
					resourceId: 'resource-1',
					status: 'ok',
					resource: defaultResource
				}
			}
		});

		expect(view.body).toContain('Ressource mobilite communale');
		expect(view.body).toContain('Dataset mobilite');
		expect(view.body).toContain('href="/dataset/dataset-1"');
		expect(view.body).toContain('Ouvrir l URL source');
		expect(view.body).toContain('href="/"');
		expect(view.body).toContain('Previsualisation courte');
		expect(view.body).toContain('Apercu CSV');
	});

	it('affiche les fallbacks non renseigne quand les valeurs sont absentes', () => {
		const view = render(Page, {
			props: {
				data: {
					resourceId: 'resource-2',
					status: 'ok',
					resource: {
						...defaultResource,
						format: null,
						size_bytes: null,
						created: null,
						last_modified: null,
						dataset_title: null,
						dataset_id: null,
						url: null
					}
				}
			}
		});

		expect(view.body).toContain('Non renseigne');
		expect(view.body).toContain('Non renseignee');
		expect(view.body).not.toContain('Retour a la fiche dataset');
		expect(view.body).not.toContain('Ouvrir l URL source');
		expect(view.body).toContain('Previsualisation non disponible pour le format inconnu');
	});

	it('affiche une previsualisation non disponible pour un format non compatible', () => {
		const view = render(Page, {
			props: {
				data: {
					resourceId: 'resource-xlsx',
					status: 'ok',
					resource: {
						...defaultResource,
						format: 'XLSX'
					}
				}
			}
		});

		expect(view.body).toContain('Previsualisation courte');
		expect(view.body).toContain('Previsualisation non disponible pour le format XLSX');
	});

	it('garde un message explicite en cas d erreur backend', () => {
		const view = render(Page, {
			props: {
				data: {
					resourceId: 'resource-3',
					status: 'error',
					errorMessage: 'Erreur API 500'
				}
			}
		});

		expect(view.body).toContain('Erreur API 500');
		expect(view.body).toContain('Retour a la recherche');
	});

	it('propose une sortie claire quand la ressource est introuvable', () => {
		const view = render(Page, {
			props: {
				data: {
					resourceId: 'introuvable',
					status: 'not-found'
				}
			}
		});

		expect(view.body).toContain('Ressource introuvable: introuvable');
		expect(view.body).toContain('Retour a la recherche');
	});

	it('preserve le contexte de recherche sur les liens de retour', () => {
		const view = render(Page, {
			props: {
				data: {
					resourceId: 'resource-1',
					status: 'ok',
					searchContext: 'q=mobilite&sort=quality_desc&page=2&org=org-1&fmt=CSV&tag=transport',
					resource: defaultResource
				}
			}
		});

		expect(view.body).toContain(
			'href="/?q=mobilite&amp;sort=quality_desc&amp;page=2&amp;org=org-1&amp;fmt=CSV&amp;tag=transport"'
		);
		expect(view.body).toContain(
			'href="/dataset/dataset-1?ctx=q%3Dmobilite%26sort%3Dquality_desc%26page%3D2%26org%3Dorg-1%26fmt%3DCSV%26tag%3Dtransport"'
		);
	});

	it('desactive le lien source quand l URL externe est non conforme', () => {
		const view = render(Page, {
			props: {
				data: {
					resourceId: 'resource-evil',
					status: 'ok',
					resource: {
						...defaultResource,
						url: 'javascript:alert(1)'
					}
				}
			}
		});

		expect(view.body).toContain('URL source non conforme');
		expect(view.body).not.toContain('href="javascript:alert(1)"');
	});
});
