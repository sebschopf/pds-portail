/** Types pour le service de surveillance de datasets (SPEC-009, ADR-028, PDS-90). */

/** Représentation du watcher côté frontend. */
export type Watcher = {
	id: string;
	email: string;
	plan: 'monthly' | 'yearly';
	status: 'active' | 'cancelled' | 'paused';
	token: string;
	created_at: string; // ISO 8601
	updated_at: string; // ISO 8601
};

/** Dataset surveillé par un watcher. */
export type WatchedDataset = {
	id: string;
	watcher_id: string;
	dataset_id: string;
	dataset_title?: string; // Enrichi côté frontend pour l'affichage
	last_known_metadata_modified: string | null;
	last_known_resource_count: number | null;
	last_known_quality_score: number | null;
	created_at: string; // ISO 8601
};

/** Historique d'une alerte sur un changement détecté. */
export type ChangeLog = {
	id: string;
	dataset_id: string;
	change_type: 'metadata_updated' | 'resource_added' | 'resource_removed' | 'quality_degraded' | 'link_broken';
	previous_value: string | null;
	new_value: string | null;
	detected_at: string; // ISO 8601
	notified_at: string | null; // ISO 8601
};

/** Réponse de l'API GET /api/v1/watchers?token=xxx */
export type WatchersResponse = {
	watcher: Watcher;
	watched_datasets: WatchedDataset[];
};

/** Réponse de l'API GET /api/v1/alerts?token=xxx */
export type AlertsResponse = {
	changes: ChangeLog[];
	dataset_details: Record<string, { title: string; id: string }>;
};

/** État local du composant WatchDataset. */
export type WatchDatasetState = 'idle' | 'modal' | 'pending' | 'active' | 'error';
