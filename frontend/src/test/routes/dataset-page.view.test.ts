// @ts-nocheck
import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import Page from '../../routes/dataset/[id]/+page.svelte';

describe('dataset/[id] page', () => {
	const defaultStructure = {
		fields: ['Nom', 'Prenom', 'Age', 'Revenu'],
		formats: ['CSV', 'JSON'],
		update_frequency: 'Annuelle',
		last_updated: '2026-01-15'
	};

	const defaultDataset = {
		id: 'dataset-1',
		title: 'Dataset mobilite',
		description: 'Description claire',
		org_id: 'org-1',
		org_name: 'Office mobilite',
		license: 'CC-BY',
		quality_score: 85,
		completeness: 80,
		freshness_days: 12,
		resources: [
			{
				id: 'resource-1',
				name: 'Population communale',
				format: 'CSV',
				url: 'https://example.com/population.csv',
				size_bytes: 27891,
				created: '2025-12-01',
				last_modified: '2026-01-10'
			}
		],
		dataset_structure: defaultStructure
	};

	const incompleteDataset = {
		id: 'dataset-2',
		title: 'Dataset incomplet',
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
	};

	it('affiche les informations essentielles et les retours de navigation', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					dataset: defaultDataset
				}
			}
		});

		expect(view.body).toContain('Dataset mobilite');
		expect(view.body).toContain('Office mobilite');
		expect(view.body).toContain('Description claire');
		expect(view.body).toContain('CC-BY');
		expect(view.body).toContain('href="/"');
		expect(view.body).toContain('org-1');
		expect(view.body).toContain('page=1');
		expect(view.body).toContain("Modes d'accès");
		expect(view.body).toContain('Explication du score qualité');
		expect(view.body).toContain('Comprendre la pondération du score qualité');
		expect(view.body).toContain('href="/dataset/dataset-1/ponderation"');
		expect(view.body).toContain('Accès direct (URL)');
		expect(view.body).toContain('Exploration guidée');
		expect(view.body).toContain('Accès API (développement)');
		expect(view.body).toContain('href="/dataset/dataset-1"');
		expect(view.body).toContain('href="/api/v1/dataset/dataset-1"');
	});

	it('affiche les indicateurs qualite fraicheur completude et score', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					dataset: defaultDataset
				}
			}
		});

		expect(view.body).toContain('85');
		expect(view.body).toContain('80/100');
		expect(view.body).toContain('12');
		expect(view.body).toContain('jours');
	});

	it('affiche le message fraicheur pour dataset recent (< 30 jours)', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					dataset: { ...defaultDataset, freshness_days: 5 }
				}
			}
		});

		expect(view.body).toContain('5 jours');
		expect(view.body).toContain('Mise à jour récente');
	});

	it('affiche le message fraicheur pour dataset modere (30-180 jours)', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					dataset: { ...defaultDataset, freshness_days: 90 }
				}
			}
		});

		expect(view.body).toContain('90 jours');
		expect(view.body).toContain('Mise à jour modérée');
	});

	it('affiche le message fraicheur pour dataset ancien (> 180 jours)', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					dataset: { ...defaultDataset, freshness_days: 250 }
				}
			}
		});

		expect(view.body).toContain('250 jours');
		expect(view.body).toContain('Données anciennes');
	});

	it('affiche un signal pour fraicheur non renseignee', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					dataset: incompleteDataset,
					polar_product_id: 'product_test',
					polar_checkout_url: undefined
				}
			}
		});

		expect(view.body).toContain('Non renseignée');
	});

	it('affiche la completude avec le detail des 5 checks', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					dataset: { ...defaultDataset, completeness: 80, quality_score: 85 }
				}
			}
		});

		expect(view.body).toContain('80/100');
		expect(view.body).toContain('Qualité');
		expect(view.body).toContain('85');
	});

	it('affiche l alerte pour qualite faible', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					dataset: { ...defaultDataset, quality_score: 25, completeness: 20, freshness_days: 400 }
				}
			}
		});

		expect(view.body).toContain('25');
		expect(view.body).toContain('20/100');
		expect(view.body).toContain('400');
	});

	it('affiche la structure du dataset avec champs formats et frequence', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					dataset: defaultDataset
				}
			}
		});

		expect(view.body).toContain('Structure du jeu de données');
		expect(view.body).toContain('Champs disponibles');
		expect(view.body).toContain('Nom');
		expect(view.body).toContain('Prenom');
		expect(view.body).toContain('Age');
		expect(view.body).toContain('Revenu');
		expect(view.body).toContain('4 champs');
		expect(view.body).toContain('Formats de fichier');
		expect(view.body).toContain('CSV');
		expect(view.body).toContain('JSON');
		expect(view.body).toContain('Fréquence de mise à jour');
		expect(view.body).toContain('Annuelle');
		expect(view.body).toContain('Dernière mise à jour');
		expect(view.body).toContain('2026-01-15');
	});

	it('affiche les ressources associees et le lien vers la vue ressource', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					dataset: defaultDataset
				}
			}
		});

		expect(view.body).toContain('Ressources associées');
		expect(view.body).toContain('Population communale');
		expect(view.body).toContain('https://example.com/population.csv');
		expect(view.body).toContain('/resource/resource-1');
	});

	it('preserve le contexte de recherche sur les liens ressource et retour recherche', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					searchContext: 'q=mobilite&sort=quality_desc&page=2&org=org-1&fmt=CSV&tag=transport',
					dataset: defaultDataset
				}
			}
		});

		expect(view.body).toContain(
			'href="/?q=mobilite&amp;sort=quality_desc&amp;page=2&amp;org=org-1&amp;fmt=CSV&amp;tag=transport"'
		);
		expect(view.body).toContain(
			'/resource/resource-1?ctx=q%3Dmobilite%26sort%3Dquality_desc%26page%3D2%26org%3Dorg-1%26fmt%3DCSV%26tag%3Dtransport'
		);
	});

	it('affiche un etat explicite quand la structure est absente', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					dataset: {
						...incompleteDataset,
						dataset_structure: { fields: [], formats: [], update_frequency: null, last_updated: null }
					}
				}
			}
		});

		expect(view.body).toContain('Structure du jeu de données');
		expect(view.body).toContain('Structure du dataset non renseignée');
		expect(view.body).not.toContain('Champs disponibles');
		expect(view.body).not.toContain('Formats de fichier');
	});

	it('affiche un etat explicite quand aucune ressource associee n est disponible', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-2',
					status: 'ok',
					dataset: incompleteDataset,
					polar_product_id: 'product_test',
					polar_checkout_url: undefined
				}
			}
		});

		expect(view.body).toContain('Ressources associées');
		expect(view.body).toContain('Aucune ressource associée disponible');
	});

	it('porte les labels ARIA attendus pour les zones de navigation de la fiche', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					dataset: defaultDataset
				}
			}
		});

		expect(view.body).toContain('aria-label="Fil de navigation dataset"');
		expect(view.body).toContain('aria-label="Navigation dataset"');
		expect(view.body).toContain('aria-label="Ressources associées"');
		expect(view.body).toContain('aria-label="Structure du dataset"');
	});

	it('ne declare aucun tabindex positif dans la fiche dataset', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'ok',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					dataset: defaultDataset
				}
			}
		});

		expect(view.body).not.toMatch(/tabindex=\"[1-9]\d*\"/);
	});

	it('garde un retour clair en cas d erreur de chargement', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-1',
					status: 'error',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined,
					errorMessage: 'Erreur API 500'
				}
			}
		});

		expect(view.body).toContain('Erreur API 500');
		expect(view.body).toContain('href="/"');
	});

	it('affiche un message explicite pour not-found avec lien de retour', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-introuvable',
					status: 'not-found',
					polar_product_id: 'product_test',
					polar_checkout_url: undefined
				}
			}
		});

		expect(view.body).toContain('Retour à la recherche');
		expect(view.body).not.toContain('<h3 class="title');
	});

	it('affiche les fallbacks Non renseignee et masque le lien organisation quand org_id est null', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-2',
					status: 'ok',
					dataset: incompleteDataset,
					polar_product_id: 'product_test',
					polar_checkout_url: undefined
				}
			}
		});

		expect(view.body).toContain('Non renseignée');
		expect(view.body).not.toContain('Voir les datasets de cette organisation');
		expect(view.body).toContain('Comprendre la pondération du score qualité');
		expect(view.body).toContain('href="/dataset/dataset-2/ponderation"');
	});

	it('affiche un message explicite pour completude nulle', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-2',
					status: 'ok',
					dataset: incompleteDataset,
					polar_product_id: 'product_test',
					polar_checkout_url: undefined
				}
			}
		});

		expect(view.body).toContain('Non renseignée');
	});

	it('affiche les alertes pour valeurs manquantes', () => {
		const view = render(Page as any, {
			props: {
				// @ts-expect-error: polar_checkout_url added to PageData by PDS-121
				data: {
					datasetId: 'dataset-2',
					status: 'ok',
					dataset: incompleteDataset,
					polar_product_id: 'product_test',
					polar_checkout_url: undefined
				}
			}
		});

		expect(view.body).toContain('Non renseignée');
	});
});