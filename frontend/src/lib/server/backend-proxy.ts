import { env } from '$env/dynamic/public';

const DEFAULT_BACKEND_BASE_URL = 'http://127.0.0.1:8000';

export async function forwardToBackend(fetch: typeof globalThis.fetch, path: string): Promise<Response> {
	const backendBaseUrl = env.PUBLIC_API_BASE_URL || DEFAULT_BACKEND_BASE_URL;
	const targetUrl = new URL(path, backendBaseUrl);
	return fetch(targetUrl);
}
