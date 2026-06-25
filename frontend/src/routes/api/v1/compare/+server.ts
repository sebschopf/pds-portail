import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

const DEFAULT_BACKEND_BASE_URL = 'http://127.0.0.1:8000';

/**
 * POST /api/v1/compare — Proxy vers le backend FastAPI (PDS-43).
 * Transmet les IDs de datasets a comparer et retourne les champs homogenes.
 *
 * Contrairement a forwardToBackend (GET-only), cet endpoint gere le POST
 * en relayant explicitement le corps JSON et les headers.
 */
export const POST: RequestHandler = async ({ request, fetch }: { request: Request; fetch: typeof globalThis.fetch }) => {
	const body = await request.text();

	if (env.PUBLIC_USE_MOCK_API !== '1') {
		const backendBaseUrl = env.PUBLIC_API_BASE_URL || DEFAULT_BACKEND_BASE_URL;
		const targetUrl = `${backendBaseUrl}/api/v1/compare`;

		const upstream = await fetch(targetUrl, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body,
		});

		const headers = new Headers(upstream.headers);
		// Empêche les incohérences de décodage quand la réponse est relayée par SvelteKit.
		headers.delete('content-encoding');
		headers.delete('content-length');
		headers.delete('transfer-encoding');

		return new Response(upstream.body, {
			status: upstream.status,
			statusText: upstream.statusText,
			headers,
		});
	}

	// Mode mock : simule une reponse de comparaison
	const { ids } = JSON.parse(body);
	const mockItems = ids.map((id: string) => ({
		id,
		title: `Dataset ${id.slice(0, 8)}`,
		org_name: 'Organisation exemple',
		description: 'Description simulee pour le dataset.',
		license: 'CC-BY 4.0',
		quality_score: Math.floor(Math.random() * 100),
		completeness: Math.floor(Math.random() * 100),
		freshness_days: Math.floor(Math.random() * 365),
		resource_formats: ['CSV', 'JSON'],
		resource_count: Math.floor(Math.random() * 10) + 1,
		tags: ['exemple', 'mock', 'comparaison'],
		ckan_url: null,
	}));

	return json({ items: mockItems });
};