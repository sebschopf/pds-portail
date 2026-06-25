/**
 * Type guards utilitaires partagés entre les contrats.
 * Évite la duplication de isNullableString / isNullableNumber.
 */

export function isNullableString(value: unknown): value is string | null {
	return typeof value === 'string' || value === null;
}

export function isNullableNumber(value: unknown): value is number | null {
	return typeof value === 'number' || value === null;
}