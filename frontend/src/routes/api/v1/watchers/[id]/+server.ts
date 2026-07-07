import { forwardToBackend } from '$lib/server/backend-proxy';
import type { RequestHandler } from '@sveltejs/kit';

/** DELETE /api/v1/watchers/{id}?token=... — supprime une surveillance dataset. */
export const DELETE: RequestHandler = async ({ fetch, params, url }) => {
	const token = url.searchParams.get('token') || '';
	const id = params.id || '';

	return forwardToBackend(
		fetch,
		`/api/v1/watchers/${encodeURIComponent(id)}?token=${encodeURIComponent(token)}`,
		{ method: 'DELETE' }
	);
};