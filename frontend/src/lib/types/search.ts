import type { RankingSignals } from './ranking';

/** Contrat d'un item dataset dans la reponse de recherche (backend ou mock). */
export type SearchDatasetItem = {
	id: string;
	title: string;
	org_name: string | null;
	description: string | null;
	quality_score: number | null;
	completeness: number | null;
	freshness_days: number | null;
	resource_formats: string[];
	resource_count: number;
	tags: string[];
	ranking_signals?: RankingSignals | null;
};

/** Facette renvoyee par l'API de recherche. */
export type FacetItem = {
	name: string;
	count: number;
	display_name?: string;
};

/** Contrat complet de la reponse /api/v1/search. */
export type SearchResponse = {
	total: number;
	offset: number;
	limit: number;
	datasets: SearchDatasetItem[];
	facets?: {
		organizations: FacetItem[];
		formats: FacetItem[];
		tags: FacetItem[];
	};
};