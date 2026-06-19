import { env } from '$env/dynamic/public';

const DEFAULT_BACKEND_BASE_URL = 'http://127.0.0.1:8000';

export async function forwardToBackend(fetch: typeof globalThis.fetch, path: string): Promise<Response> {
	const backendBaseUrl = env.PUBLIC_API_BASE_URL || DEFAULT_BACKEND_BASE_URL;
	const targetUrl = new URL(path, backendBaseUrl);
	const upstreamResponse = await fetch(targetUrl);

	const headers = new Headers(upstreamResponse.headers);
	// Empêche les incohérences de décodage quand la réponse est relayée par l'endpoint SvelteKit.
	headers.delete('content-encoding');
	headers.delete('content-length');
	headers.delete('transfer-encoding');

	return new Response(upstreamResponse.body, {
		status: upstreamResponse.status,
		statusText: upstreamResponse.statusText,
		headers
	});
}
