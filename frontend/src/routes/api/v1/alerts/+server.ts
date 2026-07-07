import { forwardToBackend } from '$lib/server/backend-proxy';
import type { RequestHandler } from '@sveltejs/kit';

/** GET /api/v1/alerts?token=... — historique des changements pour les datasets surveillés. */
export const GET: RequestHandler = async ({ fetch, url }) => {
	const token = url.searchParams.get('token') || '';
	return forwardToBackend(fetch, `/api/v1/alerts?token=${encodeURIComponent(token)}`);
};