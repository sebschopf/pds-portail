import { forwardToBackend } from '$lib/server/backend-proxy';
import { json, type RequestHandler } from '@sveltejs/kit';

/** POST /api/v1/magic-link — demande un magic link par email. */
export const POST: RequestHandler = async ({ fetch, request }) => {
	const body = await request.json();
	return forwardToBackend(fetch, '/api/v1/magic-link', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
};