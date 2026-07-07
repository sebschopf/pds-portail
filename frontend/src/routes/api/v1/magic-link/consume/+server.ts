import { forwardToBackend } from '$lib/server/backend-proxy';
import type { RequestHandler } from '@sveltejs/kit';

/** GET /api/v1/magic-link/consume?magic=... — consomme un magic link. */
export const GET: RequestHandler = async ({ fetch, url }) => {
	const magic = url.searchParams.get('magic') || '';
	return forwardToBackend(fetch, `/api/v1/magic-link/consume?magic=${encodeURIComponent(magic)}`);
};