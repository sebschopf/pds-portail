import type { components } from './api.generated';

/**
 * Types de recherche — alias vers le contrat OpenAPI généré automatiquement.
 * SPEC-016 / ADR-035 : source de vérité unique backend↔frontend.
 */
export type SearchDatasetItem = components['schemas']['SearchDatasetItem'];
export type FacetItem = components['schemas']['FacetItem'];
export type SearchResponse = components['schemas']['SearchResponse'];