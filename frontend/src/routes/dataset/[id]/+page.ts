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
	polar_checkout_url?: string;
};

export const load: PageLoad<DatasetPageData> = async ({ fetch, params, url }) => {
	const datasetId = params.id;
	const searchContext = normalizeSearchContext(url?.searchParams?.get('ctx'));
	const contextData = searchContext ? { searchContext } : {};
	const polarProductId = env.PUBLIC_POLAR_PRODUCT_ID || undefined;
	const polarCheckoutUrl = env.PUBLIC_POLAR_CHECKOUT_URL || undefined;
	console.log('[PDS-121 DEBUG] PUBLIC_POLAR_PRODUCT_ID:', polarProductId, 'PUBLIC_POLAR_CHECKOUT_URL:', polarCheckoutUrl);
	const response = await fetch(`/api/v1/dataset/${encodeURIComponent(datasetId)}`);

	if (response.status === 404) {
		return {
			datasetId,
			status: 'not-found',
			...contextData,
			polar_product_id: polarProductId,
			polar_checkout_url: polarCheckoutUrl
		};
	}

	if (!response.ok) {
		return {
			datasetId,
			status: 'error',
			...contextData,
			errorMessage: `Erreur API ${response.status}`,
			polar_product_id: polarProductId,
			polar_checkout_url: polarCheckoutUrl
		};
	}

	const payload = (await response.json()) as unknown;
	if (!isDatasetDetailContract(payload)) {
		return {
			datasetId,
			status: 'contract-error',
			...contextData,
			polar_product_id: polarProductId,
			polar_checkout_url: polarCheckoutUrl
		};
	}

	return {
		datasetId,
		status: 'ok',
		...contextData,
		dataset: payload,
		polar_product_id: polarProductId,
		polar_checkout_url: polarCheckoutUrl
	};
};