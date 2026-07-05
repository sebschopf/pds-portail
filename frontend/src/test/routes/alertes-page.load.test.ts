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

	it('charge les données watchers et alerts quand un token URL valide est fourni', async () => {
		const mockWatchers = {
			watcher: {
				id: 'watcher-1',
				email: 'test@example.ch',
				plan: 'monthly' as const,
				status: 'active' as const,
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
		};

		const mockAlerts = {
			changes: [
				{
					id: 'change-1',
					dataset_id: 'dataset-1',
					change_type: 'metadata_updated' as const,
					previous_value: 'Old title',
					new_value: 'New title',
					detected_at: '2026-01-05T12:00:00Z',
					notified_at: '2026-01-05T12:05:00Z'
				}
			],
			dataset_details: {
				'dataset-1': { title: 'Test Dataset', id: 'dataset-1' }
			}
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
		expect(data.watchers?.watcher.email).toBe('test@example.ch');
		expect(data.watchers?.watched_datasets).toHaveLength(1);
		expect(data.alerts?.changes).toHaveLength(1);
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
		expect(data.errorMessage).toContain('Token invalide');
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
