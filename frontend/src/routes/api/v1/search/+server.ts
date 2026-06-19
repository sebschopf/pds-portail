import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

import { buildSearchRecords } from '$lib/mock/mock-api-data';
import { forwardToBackend } from '$lib/server/backend-proxy';

type SortValue =
	| 'modified_desc'
	| 'modified_asc'
	| 'quality_desc'
	| 'quality_asc'
	| 'title_asc'
	| 'title_desc';

function parseQueryTerms(rawQuery: string): string[] {
	const terms: string[] = [];
	const matcher = /"([^"]+)"|(\S+)/g;
	let match: RegExpExecArray | null = matcher.exec(rawQuery.toLowerCase());
	while (match) {
		terms.push((match[1] || match[2]).toLowerCase());
		match = matcher.exec(rawQuery.toLowerCase());
	}
	return terms;
}

function toInteger(value: string | null, fallbackValue: number): number {
	if (!value) {
		return fallbackValue;
	}
	const parsed = Number.parseInt(value, 10);
	return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallbackValue;
}

function sortDatasets(datasets: ReturnType<typeof buildSearchRecords>, sort: SortValue) {
	const copied = [...datasets];
	copied.sort((a, b) => {
		if (sort === 'title_asc') return a.title.localeCompare(b.title);
		if (sort === 'title_desc') return b.title.localeCompare(a.title);
		if (sort === 'quality_asc') return (a.quality_score ?? -1) - (b.quality_score ?? -1);
		if (sort === 'quality_desc') return (b.quality_score ?? -1) - (a.quality_score ?? -1);
		if (sort === 'modified_asc') return (a.freshness_days ?? 99999) - (b.freshness_days ?? 99999);
		return (b.freshness_days ?? 99999) - (a.freshness_days ?? 99999);
	});
	return copied;
}

export const GET: RequestHandler = async ({ url }) => {
	if (env.PUBLIC_USE_MOCK_API !== '1') {
		return forwardToBackend(fetch, `/api/v1/search${url.search}`);
	}

	const query = (url.searchParams.get('q') ?? '').trim();
	const org = (url.searchParams.get('org') ?? '').trim();
	const format = (url.searchParams.get('fmt') ?? '').trim();
	const sort = (url.searchParams.get('sort') ?? 'modified_desc') as SortValue;
	const offset = toInteger(url.searchParams.get('offset'), 0);
	const limit = Math.max(1, toInteger(url.searchParams.get('limit'), 10));

	const terms = parseQueryTerms(query);
	const records = buildSearchRecords();

	const filtered = records.filter((dataset) => {
		if (org && dataset.id !== org && dataset.org_name !== org) {
			return false;
		}
		if (format && !dataset.resource_formats.includes(format)) {
			return false;
		}
		if (terms.length === 0) {
			return true;
		}

		const haystack = [
			dataset.title,
			dataset.description ?? '',
			dataset.org_name ?? '',
			dataset.tags.join(' '),
			dataset.resource_formats.join(' ')
		]
			.join(' ')
			.toLowerCase();

		return terms.every((term) => haystack.includes(term));
	});

	const ordered = sortDatasets(filtered, sort);
	const datasets = ordered.slice(offset, offset + limit);

	const organizationsMap = new Map<string, { name: string; count: number; display_name: string }>();
	const formatsMap = new Map<string, { name: string; count: number }>();
	const tagsMap = new Map<string, { name: string; count: number }>();

	for (const dataset of filtered) {
		if (dataset.org_name) {
			const current = organizationsMap.get(dataset.id) ?? {
				name: dataset.id,
				count: 0,
				display_name: dataset.org_name
			};
			current.count += 1;
			organizationsMap.set(dataset.id, current);
		}

		for (const fmt of dataset.resource_formats) {
			const current = formatsMap.get(fmt) ?? { name: fmt, count: 0 };
			current.count += 1;
			formatsMap.set(fmt, current);
		}

		for (const tag of dataset.tags) {
			const current = tagsMap.get(tag) ?? { name: tag, count: 0 };
			current.count += 1;
			tagsMap.set(tag, current);
		}
	}

	return json({
		total: filtered.length,
		offset,
		limit,
		datasets,
		facets: {
			organizations: Array.from(organizationsMap.values()).sort((a, b) => b.count - a.count),
			formats: Array.from(formatsMap.values()).sort((a, b) => b.count - a.count),
			tags: Array.from(tagsMap.values()).sort((a, b) => b.count - a.count)
		}
	});
};
