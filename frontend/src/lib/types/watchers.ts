/** Types pour le service de surveillance de datasets (SPEC-009, ADR-028, PDS-90). */

/** Dataset surveillé exposé par GET /api/v1/watchers. */
export type WatchedDataset = {
	id: string;
	dataset_id: string;
	dataset_title: string | null;
	created_at: string;
};

/** Historique d'une alerte sur un changement détecté. */
export type ChangeLog = {
	id: string;
	dataset_id: string;
	dataset_title: string | null;
	change_type: 'metadata_updated' | 'resource_added' | 'resource_removed' | 'quality_degraded' | 'link_broken';
	previous_value: string | null;
	new_value: string | null;
	detected_at: string; // ISO 8601
	notified_at: string | null; // ISO 8601
};

/** Réponse de l'API GET /api/v1/watchers?token=xxx */
export type WatchersResponse = {
	watcher_id: string;
	email: string;
	status: 'active' | 'suspended' | 'cancelled';
	items: WatchedDataset[];
};

/** Réponse de l'API GET /api/v1/alerts?token=xxx */
export type AlertsResponse = {
	watcher_id: string;
	count: number;
	items: ChangeLog[];
};

/** État local du composant WatchDataset. */
export type WatchDatasetState = 'idle' | 'modal' | 'pending' | 'active' | 'error';
