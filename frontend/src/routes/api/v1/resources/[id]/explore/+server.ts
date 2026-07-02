import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

import { forwardToBackend } from '$lib/server/backend-proxy';

type MockExploreResponse = {
	resource_id: string;
	format: string;
	parsed_at: string;
	columns: Array<{
		name: string;
		detected_type: string;
		fill_rate: number;
		sample_values: string[];
		stats: {
			min: number | null;
			max: number | null;
			mean: number | null;
			median: number | null;
		} | null;
	}>;
	row_count: number;
	analysis: {
		summary: string;
		capabilities: string[];
		caveats: string[];
	};
	cached: boolean;
};

function buildMockExploreResponse(resourceId: string): MockExploreResponse {
	return {
		resource_id: resourceId,
		format: 'csv',
		parsed_at: new Date('2026-07-02T10:00:00Z').toISOString(),
		columns: [
			{
				name: 'commune',
				detected_type: 'string',
				fill_rate: 1,
				sample_values: ['Geneve', 'Lausanne', 'Berne', 'Zurich', 'Fribourg'],
				stats: null
			},
			{
				name: 'population',
				detected_type: 'integer',
				fill_rate: 0.95,
				sample_values: ['203856', '140202', '134794', '421878', '115129'],
				stats: {
					min: 115129,
					max: 421878,
					mean: 203171.8,
					median: 140202
				}
			}
		],
		row_count: 2148,
		analysis: {
			summary: 'Ce dataset combine des mesures numeriques avec une dimension geographique.',
			capabilities: [
				'Comparer les communes entre elles',
				'Suivre des tendances demographiques',
				'Construire des visualisations de synthese'
			],
			caveats: ['Certaines valeurs manquent sur quelques lignes.']
		},
		cached: false
	};
}

export const POST: RequestHandler = async ({ params, request }) => {
	if (env.PUBLIC_USE_MOCK_API !== '1') {
		const apiKey = request.headers.get('X-API-Key') ?? '';
		return forwardToBackend(fetch, `/api/v1/resources/${encodeURIComponent(params.id)}/explore`, {
			method: 'POST',
			headers: { 'X-API-Key': apiKey },
			body: await request.text()
		});
	}

	const apiKey = request.headers.get('X-API-Key')?.trim() ?? '';
	if (apiKey.length === 0) {
		return json({ detail: 'Invalid API key' }, { status: 401 });
	}

	if (apiKey.toLowerCase() === 'quota-exhausted') {
		return json({ detail: 'Monthly quota exhausted for this key' }, { status: 429 });
	}

	if (apiKey.toLowerCase() === 'unsupported-format') {
		return json({ detail: "Format 'pdf' not supported" }, { status: 422 });
	}

	if (apiKey.toLowerCase() === 'timeout') {
		return json({ detail: 'Resource download timed out' }, { status: 504 });
	}

	return json(buildMockExploreResponse(params.id), { status: 200 });
};
