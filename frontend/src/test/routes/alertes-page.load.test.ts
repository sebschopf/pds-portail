import { describe, expect, it, vi } from 'vitest';

import { load } from '../../routes/alertes/+page';

describe('alertes (+page.ts) load', () => {
	it('retourne not-authenticated sans token URL', async () => {
		const data = await load({
			url: new URL('http://localhost:5173/alertes'),
			fetch: vi.fn()
		} as never);

		expect(data.status).toBe('not-authenticated');
	});

	it('consomme un magic link valide et charge les données (ADR-030)', async () => {
		const mockConsumed = {
			token: 'permanent-token-123',
			watcher_id: 'watcher-1',
			email: 'test@example.ch',
			status: 'active'
		};

		const mockWatchers = {
			watcher_id: 'watcher-1',
			email: 'test@example.ch',
			status: 'active' as const,
			items: [
				{
					id: 'watched-1',
					dataset_id: 'dataset-1',
					dataset_title: 'Test Dataset',
					created_at: '2026-01-01T00:00:00Z'
				}
			]
		};

		const mockAlerts = {
			watcher_id: 'watcher-1',
			count: 1,
			items: [
				{
					id: 'change-1',
					dataset_id: 'dataset-1',
					dataset_title: 'Test Dataset',
					change_type: 'metadata_updated' as const,
					previous_value: 'Old title',
					new_value: 'New title',
					detected_at: '2026-01-05T12:00:00Z',
					notified_at: '2026-01-05T12:05:00Z'
				}
			]
		};

		const mockFetch = vi.fn((url: string) => {
			if (url.includes('/api/v1/magic-link/consume')) {
				return Promise.resolve(new Response(JSON.stringify(mockConsumed), { status: 200 }));
			}
			if (url.includes('/api/v1/watchers')) {
				return Promise.resolve(new Response(JSON.stringify(mockWatchers), { status: 200 }));
			}
			if (url.includes('/api/v1/alerts')) {
				return Promise.resolve(new Response(JSON.stringify(mockAlerts), { status: 200 }));
			}
			return Promise.resolve(new Response('Not found', { status: 404 }));
		});

		const data = await load({
			url: new URL('http://localhost:5173/alertes?magic=magic-token-brut'),
			fetch: mockFetch
		} as never);

		expect(data.status).toBe('success');
		expect(data.token).toBe('permanent-token-123');
		expect(data.watchers?.email).toBe('test@example.ch');
	});

	it('affiche un message si le magic link est expiré', async () => {
		const mockFetch = vi.fn((url: string) => {
			if (url.includes('/api/v1/magic-link/consume')) {
				return Promise.resolve(
					new Response(
						JSON.stringify({ detail: 'Magic link expiré' }),
						{ status: 401 }
					)
				);
			}
			return Promise.resolve(new Response('Not found', { status: 404 }));
		});

		const data = await load({
			url: new URL('http://localhost:5173/alertes?magic=expired-token'),
			fetch: mockFetch
		} as never);

		expect(data.status).toBe('not-authenticated');
		expect(data.errorMessage).toContain('expiré');
	});

	it('affiche un message si le magic link a déjà été utilisé', async () => {
		const mockFetch = vi.fn((url: string) => {
			if (url.includes('/api/v1/magic-link/consume')) {
				return Promise.resolve(
					new Response(
						JSON.stringify({ detail: 'Magic link déjà utilisé' }),
						{ status: 401 }
					)
				);
			}
			return Promise.resolve(new Response('Not found', { status: 404 }));
		});

		const data = await load({
			url: new URL('http://localhost:5173/alertes?magic=used-token'),
			fetch: mockFetch
		} as never);

		expect(data.status).toBe('not-authenticated');
		expect(data.errorMessage).toContain('déjà été utilisé');
	});

	it('charge les données watchers et alerts quand un token URL valide est fourni', async () => {
		const mockWatchers = {
			watcher_id: 'watcher-1',
			email: 'test@example.ch',
			status: 'active' as const,
			items: [
				{
					id: 'watched-1',
					dataset_id: 'dataset-1',
					dataset_title: 'Test Dataset',
					created_at: '2026-01-01T00:00:00Z'
				}
			]
		};

		const mockAlerts = {
			watcher_id: 'watcher-1',
			count: 1,
			items: [
				{
					id: 'change-1',
					dataset_id: 'dataset-1',
					dataset_title: 'Test Dataset',
					change_type: 'metadata_updated' as const,
					previous_value: 'Old title',
					new_value: 'New title',
					detected_at: '2026-01-05T12:00:00Z',
					notified_at: '2026-01-05T12:05:00Z'
				}
			]
		};

		const mockFetch = vi.fn((url: string) => {
			if (url.includes('/api/v1/watchers')) {
				return Promise.resolve(new Response(JSON.stringify(mockWatchers), { status: 200 }));
			}
			if (url.includes('/api/v1/alerts')) {
				return Promise.resolve(new Response(JSON.stringify(mockAlerts), { status: 200 }));
			}
			return Promise.resolve(new Response('Not found', { status: 404 }));
		});

		const data = await load({
			url: new URL('http://localhost:5173/alertes?token=token-123'),
			fetch: mockFetch
		} as never);

		expect(data.status).toBe('success');
		expect(data.token).toBe('token-123');
		expect(data.watchers?.email).toBe('test@example.ch');
		expect(data.watchers?.items).toHaveLength(1);
		expect(data.alerts?.items).toHaveLength(1);
	});

	it('retourne not-authenticated quand le token est invalide (401)', async () => {
		const mockFetch = vi.fn(async () =>
			new Response('Unauthorized', { status: 401 })
		);

		const data = await load({
			url: new URL('http://localhost:5173/alertes?token=invalid-token'),
			fetch: mockFetch
		} as never);

		expect(data.status).toBe('not-authenticated');
		expect(data.errorMessage).toBe('Token invalide');
	});

	it('retourne error en cas de problème serveur', async () => {
		const mockFetch = vi.fn(async () =>
			new Response('Server error', { status: 500 })
		);

		const data = await load({
			url: new URL('http://localhost:5173/alertes?token=token-123'),
			fetch: mockFetch
		} as never);

		expect(data.status).toBe('error');
		expect(data.errorMessage).toContain('Impossible de charger');
	});
});
