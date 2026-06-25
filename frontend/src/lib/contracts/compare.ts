import type { CompareItem, CompareResponse } from '$lib/types/compare';
import { isNullableString, isNullableNumber } from '$lib/contracts/guards';

export function isCompareItem(payload: unknown): payload is CompareItem {
	if (typeof payload !== 'object' || payload === null) {
		return false;
	}

	const record = payload as Record<string, unknown>;
	return (
		typeof record.id === 'string' &&
		typeof record.title === 'string' &&
		isNullableString(record.org_name) &&
		isNullableString(record.description) &&
		isNullableString(record.license) &&
		isNullableNumber(record.quality_score) &&
		isNullableNumber(record.completeness) &&
		isNullableNumber(record.freshness_days) &&
		Array.isArray(record.resource_formats) &&
		record.resource_formats.every((f: unknown) => typeof f === 'string') &&
		typeof record.resource_count === 'number' &&
		Array.isArray(record.tags) &&
		record.tags.every((t: unknown) => typeof t === 'string') &&
		isNullableString(record.ckan_url)
	);
}

export function isCompareResponse(payload: unknown): payload is CompareResponse {
	if (typeof payload !== 'object' || payload === null) {
		return false;
	}

	const record = payload as Record<string, unknown>;
	return (
		Array.isArray(record.items) &&
		record.items.every(isCompareItem)
	);
}