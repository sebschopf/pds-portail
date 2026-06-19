import type { PageLoad } from './$types';
import { normalizeSearchContext } from '$lib/navigation/search-context';

type ResourceDetailContract = {
	id: string;
	name: string;
	format: string | null;
	url: string | null;
	size_bytes: number | null;
	created: string | null;
	last_modified: string | null;
	dataset_id: string | null;
	dataset_title: string | null;
};

type ResourcePageData = {
	resourceId: string;
	status: 'ok' | 'not-found' | 'error' | 'contract-error';
	searchContext?: string | null;
	resource?: ResourceDetailContract;
	errorMessage?: string;
};

function isNullableString(value: unknown): value is string | null {
	return typeof value === 'string' || value === null;
}

function isNullableNumber(value: unknown): value is number | null {
	return typeof value === 'number' || value === null;
}

function isResourceDetailContract(payload: unknown): payload is ResourceDetailContract {
	if (typeof payload !== 'object' || payload === null) {
		return false;
	}

	const record = payload as Record<string, unknown>;
	return (
		typeof record.id === 'string' &&
		typeof record.name === 'string' &&
		isNullableString(record.format) &&
		isNullableString(record.url) &&
		isNullableNumber(record.size_bytes) &&
		isNullableString(record.created) &&
		isNullableString(record.last_modified) &&
		isNullableString(record.dataset_id) &&
		isNullableString(record.dataset_title)
	);
}

export const load: PageLoad<ResourcePageData> = async ({ fetch, params, url }) => {
	const resourceId = params.id;
	const searchContext = normalizeSearchContext(url?.searchParams?.get('ctx'));
	const contextData = searchContext ? { searchContext } : {};
	const response = await fetch(`/api/v1/resource/${encodeURIComponent(resourceId)}`);

	if (response.status === 404) {
		return {
			resourceId,
			status: 'not-found',
			...contextData
		};
	}

	if (!response.ok) {
		return {
			resourceId,
			status: 'error',
			...contextData,
			errorMessage: `Erreur API ${response.status}`
		};
	}

	const payload = (await response.json()) as unknown;
	if (!isResourceDetailContract(payload)) {
		return {
			resourceId,
			status: 'contract-error',
			...contextData
		};
	}

	return {
		resourceId,
		status: 'ok',
		...contextData,
		resource: payload
	};
};
