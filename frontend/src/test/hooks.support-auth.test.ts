import { afterEach, describe, expect, it, vi } from 'vitest';

async function loadHandle() {
	vi.resetModules();
	const module = await import('../hooks.server');
	return module.handle;
}

afterEach(() => {
	vi.unstubAllEnvs();
	delete process.env.SUPPORT_INTERNAL_USERNAME;
	delete process.env.SUPPORT_INTERNAL_PASSWORD;
});

describe('hooks support auth guard', () => {
	it('laisse passer les routes hors /support', async () => {
		const handle = await loadHandle();
		const response = await handle({
			event: {
				url: new URL('http://localhost:5173/'),
				request: new Request('http://localhost:5173/')
			},
			resolve: vi.fn(async () => new Response('ok', { status: 200 }))
		} as never);

		expect(response.status).toBe(200);
	});

	it('retourne 503 sur /support si les secrets operateur ne sont pas configures', async () => {
		const handle = await loadHandle();
		const response = await handle({
			event: {
				url: new URL('http://localhost:5173/support'),
				request: new Request('http://localhost:5173/support')
			},
			resolve: vi.fn(async () => new Response('ok', { status: 200 }))
		} as never);

		expect(response.status).toBe(503);
	});

	it('retourne 401 sur /support si l auth basic est absente', async () => {
		process.env.SUPPORT_INTERNAL_USERNAME = 'support-user';
		process.env.SUPPORT_INTERNAL_PASSWORD = 'support-password';
		const handle = await loadHandle();

		const response = await handle({
			event: {
				url: new URL('http://localhost:5173/support'),
				request: new Request('http://localhost:5173/support')
			},
			resolve: vi.fn(async () => new Response('ok', { status: 200 }))
		} as never);

		expect(response.status).toBe(401);
		expect(response.headers.get('WWW-Authenticate')).toContain('Basic');
	});

	it('laisse passer /support si auth basic valide', async () => {
		process.env.SUPPORT_INTERNAL_USERNAME = 'support-user';
		process.env.SUPPORT_INTERNAL_PASSWORD = 'support-password';
		const handle = await loadHandle();
		const credentials = Buffer.from('support-user:support-password', 'utf-8').toString('base64');

		const response = await handle({
			event: {
				url: new URL('http://localhost:5173/support'),
				request: new Request('http://localhost:5173/support', {
					headers: {
						Authorization: `Basic ${credentials}`
					}
				})
			},
			resolve: vi.fn(async () => new Response('ok', { status: 200 }))
		} as never);

		expect(response.status).toBe(200);
	});
});
