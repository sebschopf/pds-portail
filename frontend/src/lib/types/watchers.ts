import type { components } from './api.generated';

/**
 * Types de surveillance et alertes — alias vers le contrat OpenAPI.
 * SPEC-016 / ADR-035 : source de vérité unique backend↔frontend.
 */

export type WatchedDataset = components['schemas']['WatchedDatasetItemResponse'];
export type ChangeLog = components['schemas']['AlertItemResponse'];
export type WatchersResponse = components['schemas']['WatchersListResponse'];
export type AlertsResponse = components['schemas']['AlertsResponse'];

/** État local du composant WatchDataset — UI-only, pas d'équivalent API. */
export type WatchDatasetState = 'idle' | 'modal' | 'pending' | 'active' | 'error';
