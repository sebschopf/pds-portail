import type { components } from './api.generated';

/**
 * Signaux de ranking hybride PDS-40 — alias vers le contrat OpenAPI strict.
 * SPEC-016 / ADR-035 : RankingSignals est un modèle Pydantic backend,
 * ce qui garantit un typage strict plutôt que dict[str, float] mou.
 */
export type RankingSignals = components['schemas']['RankingSignals'];