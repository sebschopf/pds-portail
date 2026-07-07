import { forwardToBackend } from '$lib/server/backend-proxy';
import type { RequestHandler } from '@sveltejs/kit';

/** POST /api/v1/contact — envoie le formulaire de contact. */
export const POST: RequestHandler = async ({ fetch, request }) => {
	const body = await request.json();
	return forwardToBackend(fetch, '/api/v1/contact', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
};