import type { components } from './api.generated';

/**
 * Types de comparaison — alias vers le contrat OpenAPI généré automatiquement.
 * SPEC-016 / ADR-035 : source de vérité unique backend↔frontend.
 */
export type CompareItem = components['schemas']['CompareItem'];
export type CompareResponse = components['schemas']['CompareResponse'];