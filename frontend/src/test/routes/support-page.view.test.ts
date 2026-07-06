import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import Page from '../../routes/support/+page.svelte';

describe('support (+page.svelte)', () => {
	it('affiche le formulaire et la procédure quand aucun diagnostic n est chargé', () => {
		const view = render(Page, {
			props: {
				data: {
					status: 'idle',
					email: '',
					notice: null,
					errorMessage: null,
					diagnostics: null
				}
			}
		});

		expect(view.body).toContain('Support interne protégé');
		expect(view.body).toContain('Lancer un diagnostic');
		expect(view.body).toContain('Procédure support');
	});

	it('affiche les diagnostics et l action de renvoi pour un watcher actif', () => {
		const view = render(Page, {
			props: {
				data: {
					status: 'loaded',
					email: 'watcher@example.ch',
					notice: 'resent',
					errorMessage: null,
					diagnostics: {
						watcher: {
							watcher_id: 'watcher-1',
							watcher_status: 'active',
							subscription_id_present: true,
							watched_datasets_count: 1,
							last_webhook_at: '2026-07-06T10:00:00+00:00',
							last_magic_link_at: '2026-07-06T11:00:00+00:00'
						},
						subscription: {
							watcher_id: 'watcher-1',
							subscription_state: 'active',
							subscription_id_masked: 'sub…001',
							updated_at: '2026-07-06T11:30:00+00:00'
						},
						webhooks: [
							{
								event_type: 'order.created',
								received_at: '2026-07-06T10:00:00+00:00',
								delivery_status: 'accepted',
								correlation_id: 'evt-1'
							}
						],
						magicLinks: {
							watcher_id: 'watcher-1',
							last_issued_at: '2026-07-06T11:00:00+00:00',
							last_used_at: null,
							active_unexpired_count: 1,
							expired_unconsumed_count: 0
						},
						deliverability: {
							watcher_id: 'watcher-1',
							last_send_status: 'sent',
							last_send_at: '2026-07-06T11:00:00+00:00',
							provider_message_id_masked: 'msg…123',
							recent_error_code: null,
							recent_error_count_24h: 0
						}
					}
				}
			}
		});

		expect(view.body).toContain('Magic link renvoyé avec succès.');
		expect(view.body).toContain('watcher@example.ch');
		expect(view.body).toContain('Renvoyer le magic link');
		expect(view.body).toContain('order.created');
		expect(view.body).toContain('sub…001');
	});

	it('affiche un message quand le watcher est introuvable', () => {
		const view = render(Page, {
			props: {
				data: {
					status: 'not-found',
					email: 'missing@example.ch',
					notice: null,
					errorMessage: 'Aucun watcher ne correspond à cette adresse email.',
					diagnostics: null
				}
			}
		});

		expect(view.body).toContain('Watcher introuvable');
		expect(view.body).toContain('Aucun watcher ne correspond à cette adresse email.');
	});
});