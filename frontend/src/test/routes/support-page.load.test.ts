import { afterEach, describe, expect, it, vi } from 'vitest';

import { actions, load } from '../../routes/support/+page.server';

afterEach(() => {
	vi.unstubAllEnvs();
});

describe('support (+page.server.ts) load', () => {
	it('retourne idle sans adresse email', async () => {
		const data = await load({
			url: new URL('http://localhost:5173/support'),
			fetch: vi.fn()
		} as never);

		expect(data.status).toBe('idle');
		expect(data.diagnostics).toBeNull();
	});

	it('charge les diagnostics support via les endpoints internes protégés', async () => {
		vi.stubEnv('INTERNAL_API_TOKEN', 'support-token-test');

		const lookup = {
			watcher_id: 'watcher-1',
			watcher_status: 'active',
			subscription_id_present: true,
			watched_datasets_count: 1,
			last_webhook_at: '2026-07-06T10:00:00+00:00',
			last_magic_link_at: '2026-07-06T11:00:00+00:00'
		};
		const subscription = {
			watcher_id: 'watcher-1',
			subscription_state: 'active',
			subscription_id_masked: 'sub…001',
			updated_at: '2026-07-06T11:30:00+00:00'
		};
		const webhooks = {
			watcher_id: 'watcher-1',
			items: [
				{
					event_type: 'order.created',
					received_at: '2026-07-06T10:00:00+00:00',
					delivery_status: 'accepted',
					correlation_id: 'evt-1'
				}
			]
		};
		const magicLinks = {
			watcher_id: 'watcher-1',
			last_issued_at: '2026-07-06T11:00:00+00:00',
			last_used_at: null,
			active_unexpired_count: 1,
			expired_unconsumed_count: 0
		};
		const deliverability = {
			watcher_id: 'watcher-1',
			last_send_status: 'sent',
			last_send_at: '2026-07-06T11:00:00+00:00',
			provider_message_id_masked: 'msg…123',
			recent_error_code: null,
			recent_error_count_24h: 0
		};

		const fetchMock = vi.fn((url: string) => {
			if (url.includes('/internal/support/watchers/by-email')) {
				return Promise.resolve(new Response(JSON.stringify(lookup), { status: 200 }));
			}
			if (url.includes('/subscription')) {
				return Promise.resolve(new Response(JSON.stringify(subscription), { status: 200 }));
			}
			if (url.includes('/webhooks/latest')) {
				return Promise.resolve(new Response(JSON.stringify(webhooks), { status: 200 }));
			}
			if (url.includes('/magic-links/state')) {
				return Promise.resolve(new Response(JSON.stringify(magicLinks), { status: 200 }));
			}
			if (url.includes('/email-deliverability')) {
				return Promise.resolve(new Response(JSON.stringify(deliverability), { status: 200 }));
			}
			return Promise.resolve(new Response('Not found', { status: 404 }));
		});

		const data = await load({
			url: new URL('http://localhost:5173/support?email=watcher@example.ch'),
			fetch: fetchMock
		} as never);

		expect(data.status).toBe('loaded');
		expect(data.diagnostics?.watcher.watcher_id).toBe('watcher-1');
		expect(data.diagnostics?.subscription.subscription_id_masked).toBe('sub…001');
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/internal/support/watchers/by-email?email=watcher%40example.ch'),
			expect.objectContaining({
				headers: expect.objectContaining({
					Authorization: 'Bearer support-token-test'
				})
			})
		);
	});

	it('retourne not-found quand aucun watcher ne correspond', async () => {
		vi.stubEnv('INTERNAL_API_TOKEN', 'support-token-test');

		const fetchMock = vi.fn(() => Promise.resolve(new Response('Not found', { status: 404 })));

		const data = await load({
			url: new URL('http://localhost:5173/support?email=missing@example.ch'),
			fetch: fetchMock
		} as never);

		expect(data.status).toBe('not-found');
		expect(data.errorMessage).toContain('watcher');
	});

	it('redirige vers la page support après un renvoi réussi', async () => {
		vi.stubEnv('INTERNAL_API_TOKEN', 'support-token-test');

		const fetchMock = vi.fn(() => Promise.resolve(new Response('{}', { status: 200 })));
		const formData = new FormData();
		formData.set('email', 'watcher@example.ch');
		formData.set('watcher_id', 'watcher-1');

		await expect(
			actions.resend({
				request: new Request('http://localhost:5173/support?/resend', {
					method: 'POST',
					body: formData
				}),
				fetch: fetchMock
			} as never)
		).rejects.toMatchObject({ status: 303, location: '/support?email=watcher%40example.ch&notice=resent' });
	});

	it('redirige avec notice queued quand le backend retourne dispatch_status queued', async () => {
		vi.stubEnv('INTERNAL_API_TOKEN', 'support-token-test');

		const fetchMock = vi.fn(() =>
			Promise.resolve(new Response(JSON.stringify({ dispatch_status: 'queued' }), { status: 200 }))
		);
		const formData = new FormData();
		formData.set('email', 'watcher@example.ch');
		formData.set('watcher_id', 'watcher-1');

		await expect(
			actions.resend({
				request: new Request('http://localhost:5173/support?/resend', {
					method: 'POST',
					body: formData
				}),
				fetch: fetchMock
			} as never)
		).rejects.toMatchObject({
			status: 303,
			location: '/support?email=watcher%40example.ch&notice=queued'
		});
	});

	it('redirige avec notice suspended quand le backend retourne 409', async () => {
		vi.stubEnv('INTERNAL_API_TOKEN', 'support-token-test');

		const fetchMock = vi.fn(() => Promise.resolve(new Response('{}', { status: 409 })));
		const formData = new FormData();
		formData.set('email', 'watcher@example.ch');
		formData.set('watcher_id', 'watcher-1');

		await expect(
			actions.resend({
				request: new Request('http://localhost:5173/support?/resend', {
					method: 'POST',
					body: formData
				}),
				fetch: fetchMock
			} as never)
		).rejects.toMatchObject({
			status: 303,
			location: '/support?email=watcher%40example.ch&notice=suspended'
		});
	});

	it('redirige avec notice rate-limited quand le backend retourne 429', async () => {
		vi.stubEnv('INTERNAL_API_TOKEN', 'support-token-test');

		const fetchMock = vi.fn(() => Promise.resolve(new Response('{}', { status: 429 })));
		const formData = new FormData();
		formData.set('email', 'watcher@example.ch');
		formData.set('watcher_id', 'watcher-1');

		await expect(
			actions.resend({
				request: new Request('http://localhost:5173/support?/resend', {
					method: 'POST',
					body: formData
				}),
				fetch: fetchMock
			} as never)
		).rejects.toMatchObject({
			status: 303,
			location: '/support?email=watcher%40example.ch&notice=rate-limited'
		});
	});

	it('redirige avec notice error quand le backend retourne une erreur non geree', async () => {
		vi.stubEnv('INTERNAL_API_TOKEN', 'support-token-test');

		const fetchMock = vi.fn(() => Promise.resolve(new Response('{}', { status: 500 })));
		const formData = new FormData();
		formData.set('email', 'watcher@example.ch');
		formData.set('watcher_id', 'watcher-1');

		await expect(
			actions.resend({
				request: new Request('http://localhost:5173/support?/resend', {
					method: 'POST',
					body: formData
				}),
				fetch: fetchMock
			} as never)
		).rejects.toMatchObject({
			status: 303,
			location: '/support?email=watcher%40example.ch&notice=error'
		});
	});
});