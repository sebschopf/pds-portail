export type MockResource = {
	id: string;
	name: string;
	format: string | null;
	url: string | null;
	size_bytes: number | null;
	created: string | null;
	last_modified: string | null;
};

export type MockDataset = {
	id: string;
	title: string;
	description: string | null;
	org_id: string | null;
	org_name: string | null;
	license: string | null;
	quality_score: number | null;
	completeness: number | null;
	freshness_days: number | null;
	tags: string[];
	resources: MockResource[];
	dataset_structure: {
		fields: string[];
		formats: string[];
		update_frequency: string | null;
		last_updated: string | null;
	};
};

export const MOCK_DATASETS: MockDataset[] = [
	{
		id: 'dataset-1',
		title: 'Mobilite communale 2026',
		description: 'Flux de mobilite et usage des transports publics au niveau communal.',
		org_id: 'org-mobilite',
		org_name: 'Office mobilite',
		license: 'CC-BY-4.0',
		quality_score: 87,
		completeness: 84,
		freshness_days: 9,
		tags: ['mobilite', 'transport', 'commune'],
		resources: [
			{
				id: 'resource-1',
				name: 'Trajets domicile-travail',
				format: 'CSV',
				url: 'https://example.com/data/trajets.csv',
				size_bytes: 493812,
				created: '2026-01-05',
				last_modified: '2026-06-01'
			},
			{
				id: 'resource-2',
				name: 'Arrets transports publics',
				format: 'JSON',
				url: 'https://example.com/data/arrets.json',
				size_bytes: 128402,
				created: '2026-01-05',
				last_modified: '2026-06-01'
			}
		],
		dataset_structure: {
			fields: ['commune', 'date', 'mode_transport', 'volume'],
			formats: ['CSV', 'JSON'],
			update_frequency: 'Mensuelle',
			last_updated: '2026-06-01'
		}
	},
	{
		id: 'dataset-2',
		title: 'Population cantonale',
		description: 'Indicateurs demographiques par district et tranche d age.',
		org_id: 'org-stat',
		org_name: 'Office statistique',
		license: 'OGL-CH',
		quality_score: 74,
		completeness: 79,
		freshness_days: 41,
		tags: ['demographie', 'population', 'canton'],
		resources: [
			{
				id: 'resource-3',
				name: 'Population par district',
				format: 'XLSX',
				url: 'https://example.com/data/population.xlsx',
				size_bytes: 93211,
				created: '2025-12-20',
				last_modified: '2026-05-07'
			}
		],
		dataset_structure: {
			fields: ['district', 'annee', 'tranche_age', 'population'],
			formats: ['XLSX'],
			update_frequency: 'Trimestrielle',
			last_updated: '2026-05-07'
		}
	}
];

function computeTextScore(queryTerms: string[], title: string, description: string | null): number {
	if (queryTerms.length === 0) return 0;
	const titleLower = title.toLowerCase();
	const descLower = (description ?? '').toLowerCase();
	let matched = 0;
	for (const term of queryTerms) {
		const tl = term.toLowerCase();
		if (tl && (titleLower.includes(tl) || descLower.includes(tl))) {
			matched += 1;
		}
	}
	return matched / queryTerms.length;
}

function computeFreshnessComponent(freshnessDays: number | null): number {
	if (freshnessDays === null || freshnessDays < 0) return 0;
	return Math.exp(-freshnessDays / 90);
}

function computeHybridSignals(
	queryTerms: string[],
	title: string,
	description: string | null,
	qualityScore: number | null,
	freshnessDays: number | null
): Record<string, number> | null {
	if (queryTerms.length === 0) return null;
	const textScore = computeTextScore(queryTerms, title, description);
	const qualityNormalized = (qualityScore ?? 0) / 100;
	const freshnessComponent = computeFreshnessComponent(freshnessDays);
	const weightText = 0.5;
	const weightQuality = 0.3;
	const weightFreshness = 0.2;
	const hybridScore = weightText * textScore + weightQuality * qualityNormalized + weightFreshness * freshnessComponent;
	return {
		hybrid_score: Math.round(hybridScore * 10000) / 10000,
		text_score: Math.round(textScore * 10000) / 10000,
		quality_normalized: Math.round(qualityNormalized * 10000) / 10000,
		freshness_component: Math.round(freshnessComponent * 10000) / 10000,
		weight_text: weightText,
		weight_quality: weightQuality,
		weight_freshness: weightFreshness
	};
}

export function buildSearchRecords(queryTerms: string[] = []) {
	return MOCK_DATASETS.map((dataset) => ({
		id: dataset.id,
		title: dataset.title,
		org_id: dataset.org_id,
		org_name: dataset.org_name,
		description: dataset.description,
		quality_score: dataset.quality_score,
		completeness: dataset.completeness,
		freshness_days: dataset.freshness_days,
		resource_formats: Array.from(
			new Set(dataset.resources.map((resource) => resource.format).filter((fmt): fmt is string => Boolean(fmt)))
		),
		resource_count: dataset.resources.length,
		tags: dataset.tags,
		ranking_signals: computeHybridSignals(
			queryTerms,
			dataset.title,
			dataset.description,
			dataset.quality_score,
			dataset.freshness_days
		)
	}));
}

export function findDatasetById(datasetId: string): MockDataset | undefined {
	return MOCK_DATASETS.find((dataset) => dataset.id === datasetId);
}

export function findResourceById(resourceId: string) {
	for (const dataset of MOCK_DATASETS) {
		const resource = dataset.resources.find((entry) => entry.id === resourceId);
		if (resource) {
			return {
				...resource,
				dataset_id: dataset.id,
				dataset_title: dataset.title
			};
		}
	}
	return undefined;
}
