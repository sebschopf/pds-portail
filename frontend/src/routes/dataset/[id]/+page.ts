import type { PageLoad } from './$types';

import type { DatasetDetailContract } from '$lib/contracts/dataset-detail';
import { isDatasetDetailContract } from '$lib/contracts/dataset-detail';
import { normalizeSearchContext } from '$lib/navigation/search-context';
import { env } from '$env/dynamic/public';

type DatasetPageData = {
	datasetId: string;
	status: 'ok' | 'not-found' | 'error' | 'contract-error';
	searchContext?: string | null;
	dataset?: DatasetDetailContract;
	errorMessage?: string;
	polar_product_id?: string;
};

export const load: PageLoad<DatasetPageData> = async ({ fetch, params, url }) => {
	const datasetId = params.id;
	const searchContext = normalizeSearchContext(url?.searchParams?.get('ctx'));
	const contextData = searchContext ? { searchContext } : {};
	// Read Polar product ID from dynamic public env to avoid build-time drift.
	const polarProductId = env.PUBLIC_POLAR_PRODUCT_ID || undefined;
	const response = await fetch(`/api/v1/dataset/${encodeURIComponent(datasetId)}`);

	if (response.status === 404) {
		return {
			datasetId,
			status: 'not-found',
			...contextData,
			polar_product_id: polarProductId
		};
	}

	if (!response.ok) {
		return {
			datasetId,
			status: 'error',
			...contextData,
			errorMessage: `Erreur API ${response.status}`,
			polar_product_id: polarProductId
		};
	}

	const payload = (await response.json()) as unknown;
	if (!isDatasetDetailContract(payload)) {
		return {
			datasetId,
			status: 'contract-error',
			...contextData,
			polar_product_id: polarProductId
		};
	}

	return {
		datasetId,
		status: 'ok',
		...contextData,
		dataset: payload,
		polar_product_id: polarProductId
	};
};