import type { PageLoad } from './$types';

import type { DatasetDetailContract } from '$lib/contracts/dataset-detail';
import { isDatasetDetailContract } from '$lib/contracts/dataset-detail';
import { normalizeSearchContext } from '$lib/navigation/search-context';

type DatasetPageData = {
	datasetId: string;
	status: 'ok' | 'not-found' | 'error' | 'contract-error';
	searchContext?: string | null;
	dataset?: DatasetDetailContract;
	errorMessage?: string;
};

export const load: PageLoad<DatasetPageData> = async ({ fetch, params, url }) => {
	const datasetId = params.id;
	const searchContext = normalizeSearchContext(url?.searchParams?.get('ctx'));
	const contextData = searchContext ? { searchContext } : {};
	const response = await fetch(`/api/v1/dataset/${encodeURIComponent(datasetId)}`);

	if (response.status === 404) {
		return {
			datasetId,
			status: 'not-found',
			...contextData
		};
	}

	if (!response.ok) {
		return {
			datasetId,
			status: 'error',
			...contextData,
			errorMessage: `Erreur API ${response.status}`
		};
	}

	const payload = (await response.json()) as unknown;
	if (!isDatasetDetailContract(payload)) {
		return {
			datasetId,
			status: 'contract-error',
			...contextData
		};
	}

	return {
		datasetId,
		status: 'ok',
		...contextData,
		dataset: payload
	};
};