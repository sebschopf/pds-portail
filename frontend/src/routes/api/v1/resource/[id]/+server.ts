import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

import { findResourceById } from '$lib/mock/mock-api-data';
import { forwardToBackend } from '$lib/server/backend-proxy';

export const GET: RequestHandler = async ({ params }) => {
	if (env.PUBLIC_USE_MOCK_API !== '1') {
		return forwardToBackend(fetch, `/api/v1/resource/${encodeURIComponent(params.id)}`);
	}

	const resource = findResourceById(params.id);
	if (!resource) {
		return json({ error: 'Ressource introuvable' }, { status: 404 });
	}

	return json(resource, { status: 200 });
};
