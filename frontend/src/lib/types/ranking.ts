/**
 * Contrat partage des signaux de ranking hybride (PDS-40).
 * Expose par le backend dans chaque SearchDatasetItem.
 * Toutes les valeurs sont dans [0, 1]. Les poids somment a 1.
 */
export type RankingSignals = {
	hybrid_score: number;
	text_score: number;
	quality_normalized: number;
	freshness_component: number;
	weight_text: number;
	weight_quality: number;
	weight_freshness: number;
};