import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

import { findDatasetById } from '$lib/mock/mock-api-data';
import { forwardToBackend } from '$lib/server/backend-proxy';

export const GET: RequestHandler = async ({ params }) => {
	if (env.PUBLIC_USE_MOCK_API !== '1') {
		return forwardToBackend(fetch, `/api/v1/dataset/${encodeURIComponent(params.id)}`);
	}

	const dataset = findDatasetById(params.id);
	if (!dataset) {
		return json({ error: 'Dataset introuvable' }, { status: 404 });
	}

	return json(dataset, { status: 200 });
};
