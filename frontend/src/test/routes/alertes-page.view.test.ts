import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import AlertesPage from '../../routes/alertes/+page.svelte';

describe('alertes (+page.svelte)', () => {
	it('affiche le formulaire de connexion quand non authentifié', () => {
		const view = render(AlertesPage, {
			props: {
				data: {
					status: 'not-authenticated',
					errorMessage: undefined,
					token: undefined
				}
			}
		});

		expect(view.body).toContain('Accéder à vos alertes');
		expect(view.body).toContain('Rappel du fonctionnement');
		expect(view.body).toContain('Vous avez changé de navigateur ou perdu l\'email');
		expect(view.body).toContain('Recevoir un lien');
	});

	it('affiche un message de suspension quand le watcher est suspendu', () => {
		const view = render(AlertesPage, {
			props: {
				data: {
					status: 'success',
					token: 'token-123',
					watchers: {
						watcher_id: 'watcher-1',
						email: 'test@example.ch',
						status: 'suspended',
						items: []
					},
					alerts: {
						watcher_id: 'watcher-1',
						count: 0,
						items: []
					}
				}
			}
		});

		expect(view.body).toContain('Votre abonnement est actuellement suspendu');
	});

	it('affiche les datasets surveillés et l\'historique des changements quand authentifié', () => {
		const view = render(AlertesPage, {
			props: {
				data: {
					status: 'success',
					token: 'token-123',
					watchers: {
						watcher_id: 'watcher-1',
						email: 'test@example.ch',
						status: 'active',
						items: [
							{
								id: 'watched-1',
								dataset_id: 'dataset-1',
								dataset_title: 'Test Dataset',
								created_at: '2026-01-01T00:00:00Z'
							}
						]
					},
					alerts: {
						watcher_id: 'watcher-1',
						count: 0,
						items: []
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
						watcher_id: 'watcher-1',
						email: 'test@example.ch',
						status: 'active',
						items: [
							{
								id: 'watched-1',
								dataset_id: 'dataset-1',
								dataset_title: 'Test Dataset',
								created_at: '2026-01-01T00:00:00Z'
							}
						]
					},
					alerts: {
						watcher_id: 'watcher-1',
						count: 1,
						items: [
							{
								id: 'change-1',
								dataset_id: 'dataset-1',
								dataset_title: 'Test Dataset',
								change_type: 'metadata_updated',
								previous_value: 'Old',
								new_value: 'New',
								detected_at: '2026-01-05T12:00:00Z',
								notified_at: '2026-01-05T12:05:00Z'
							}
						]
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
						watcher_id: 'watcher-1',
						email: 'test@example.ch',
						status: 'active',
						items: []
					},
					alerts: {
						watcher_id: 'watcher-1',
						count: 0,
						items: []
					}
				}
			}
		});

		expect(view.body).toContain('Paramètres d\'abonnement');
		expect(view.body).toContain('Le token d\'accès actuel permet de consulter vos alertes');
	});

	it('inclut un titre h1 pour l\'accessibilité', () => {
		const view = render(AlertesPage, {
			props: {
				data: {
					status: 'success',
					token: 'token-123',
					watchers: {
						watcher_id: 'watcher-1',
						email: 'test@example.ch',
						status: 'active',
						items: []
					},
					alerts: {
						watcher_id: 'watcher-1',
						count: 0,
						items: []
					}
				}
			}
		});

		// Vérifiez que le titre principal est présent
		expect(view.body).toContain('Mes alertes datasets');
	});
});
