import type { PageLoad } from './$types';

type DatasetPonderationPageData = {
	datasetId: string;
};

export const load: PageLoad<DatasetPonderationPageData> = async ({ params }) => {
	return {
		datasetId: params.id
	};
};