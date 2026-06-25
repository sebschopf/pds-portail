/** Types pour la comparaison guidee de datasets (PDS-43). */

export interface CompareItem {
	id: string;
	title: string;
	org_name: string | null;
	description: string | null;
	license: string | null;
	quality_score: number | null;
	completeness: number | null;
	freshness_days: number | null;
	resource_formats: string[];
	resource_count: number;
	tags: string[];
	ckan_url: string | null;
}

export interface CompareResponse {
	items: CompareItem[];
}