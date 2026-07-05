import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import AlertesPage from '../../routes/alertes/+page.svelte';

describe('alertes (+page.svelte)', () => {
	it('affiche le formulaire de connexion quand non authentifié', () => {
		const view = render(AlertesPage, {
			props: {
				data: {
					status: 'not-authenticated',
					token: undefined
				}
			}
		});

		expect(view.body).toContain('Accéder à vos alertes');
		expect(view.body).toContain('adresse email');
		expect(view.body).toContain('Envoyer le lien');
	});

	it('affiche les datasets surveillés et l\'historique des changements quand authentifié', () => {
		const view = render(AlertesPage, {
			props: {
				data: {
					status: 'success',
					token: 'token-123',
					watchers: {
						watcher: {
							id: 'watcher-1',
							email: 'test@example.ch',
							plan: 'monthly',
							status: 'active',
							token: 'token-123',
							created_at: '2026-01-01T00:00:00Z',
							updated_at: '2026-01-01T00:00:00Z'
						},
						watched_datasets: [
							{
								id: 'watched-1',
								watcher_id: 'watcher-1',
								dataset_id: 'dataset-1',
								dataset_title: 'Test Dataset',
								last_known_metadata_modified: '2026-01-01',
								last_known_resource_count: 5,
								last_known_quality_score: 85.5,
								created_at: '2026-01-01T00:00:00Z'
							}
						]
					},
					alerts: {
						changes: [],
						dataset_details: {
							'dataset-1': { title: 'Test Dataset', id: 'dataset-1' }
						}
					}
				}
			}
		});

		expect(view.body).toContain('Vos datasets surveillés');
		expect(view.body).toContain('Test Dataset');
		expect(view.body).toContain('Arrêter la surveillance');
	});

	it('affiche un message d\'erreur en cas de problème de chargement', () => {
		const view = render(AlertesPage, {
			props: {
				data: {
					status: 'error',
					errorMessage: 'Impossible de charger vos alertes',
					token: undefined
				}
			}
		});

		expect(view.body).toContain('Erreur de chargement');
		expect(view.body).toContain('Impossible de charger vos alertes');
	});

	it('affiche l\'historique des changements pour chaque dataset', () => {
		const view = render(AlertesPage, {
			props: {
				data: {
					status: 'success',
					token: 'token-123',
					watchers: {
						watcher: {
							id: 'watcher-1',
							email: 'test@example.ch',
							plan: 'monthly',
							status: 'active',
							token: 'token-123',
							created_at: '2026-01-01T00:00:00Z',
							updated_at: '2026-01-01T00:00:00Z'
						},
						watched_datasets: [
							{
								id: 'watched-1',
								watcher_id: 'watcher-1',
								dataset_id: 'dataset-1',
								dataset_title: 'Test Dataset',
								last_known_metadata_modified: '2026-01-01',
								last_known_resource_count: 5,
								last_known_quality_score: 85.5,
								created_at: '2026-01-01T00:00:00Z'
							}
						]
					},
					alerts: {
						changes: [
							{
								id: 'change-1',
								dataset_id: 'dataset-1',
								change_type: 'metadata_updated',
								previous_value: 'Old',
								new_value: 'New',
								detected_at: '2026-01-05T12:00:00Z',
								notified_at: '2026-01-05T12:05:00Z'
							}
						],
						dataset_details: {
							'dataset-1': { title: 'Test Dataset', id: 'dataset-1' }
						}
					}
				}
			}
		});

		expect(view.body).toContain('Historique des changements');
		expect(view.body).toContain('Métadonnées mises à jour');
	});

	it('affiche les paramètres d\'abonnement avec le bouton de désabonnement', () => {
		const view = render(AlertesPage, {
			props: {
				data: {
					status: 'success',
					token: 'token-123',
					watchers: {
						watcher: {
							id: 'watcher-1',
							email: 'test@example.ch',
							plan: 'monthly',
							status: 'active',
							token: 'token-123',
							created_at: '2026-01-01T00:00:00Z',
							updated_at: '2026-01-01T00:00:00Z'
						},
						watched_datasets: []
					},
					alerts: {
						changes: [],
						dataset_details: {}
					}
				}
			}
		});

		expect(view.body).toContain('Paramètres d\'abonnement');
		expect(view.body).toContain('Se désabonner de tous les alertes');
	});

	it('inclut un titre h1 pour l\'accessibilité', () => {
		const view = render(AlertesPage, {
			props: {
				data: {
					status: 'success',
					token: 'token-123',
					watchers: {
						watcher: {
							id: 'watcher-1',
							email: 'test@example.ch',
							plan: 'monthly',
							status: 'active',
							token: 'token-123',
							created_at: '2026-01-01T00:00:00Z',
							updated_at: '2026-01-01T00:00:00Z'
						},
						watched_datasets: []
					},
					alerts: {
						changes: [],
						dataset_details: {}
					}
				}
			}
		});

		// Vérifiez que le titre principal est présent
		expect(view.body).toContain('Mes alertes datasets');
	});
});
