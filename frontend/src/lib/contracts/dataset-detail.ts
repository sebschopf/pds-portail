export type DatasetStructureContract = {
	fields: string[];
	formats: string[];
	update_frequency: string | null;
	last_updated: string | null;
};

export type ResourceContract = {
	id: string;
	name: string;
	format: string | null;
	url: string | null;
	size_bytes: number | null;
	created: string | null;
	last_modified: string | null;
};

export type DatasetDetailContract = {
	id: string;
	title: string;
	description: string | null;
	org_id: string | null;
	org_name: string | null;
	license: string | null;
	quality_score: number | null;
	completeness: number | null;
	freshness_days: number | null;
	resources: ResourceContract[];
	dataset_structure: DatasetStructureContract;
};

function isNullableString(value: unknown): value is string | null {
	return typeof value === 'string' || value === null;
}

function isNullableNumber(value: unknown): value is number | null {
	return typeof value === 'number' || value === null;
}

export function isDatasetStructureContract(payload: unknown): payload is DatasetStructureContract {
	if (typeof payload !== 'object' || payload === null) {
		return false;
	}

	const record = payload as Record<string, unknown>;
	return (
		Array.isArray(record.fields) &&
		record.fields.every((f: unknown) => typeof f === 'string') &&
		Array.isArray(record.formats) &&
		record.formats.every((f: unknown) => typeof f === 'string') &&
		isNullableString(record.update_frequency) &&
		isNullableString(record.last_updated)
	);
}

export function isResourceContract(payload: unknown): payload is ResourceContract {
	if (typeof payload !== 'object' || payload === null) {
		return false;
	}

	const record = payload as Record<string, unknown>;
	return (
		typeof record.id === 'string' &&
		typeof record.name === 'string' &&
		isNullableString(record.format) &&
		isNullableString(record.url) &&
		isNullableNumber(record.size_bytes) &&
		isNullableString(record.created) &&
		isNullableString(record.last_modified)
	);
}

export function isDatasetDetailContract(payload: unknown): payload is DatasetDetailContract {
	if (typeof payload !== 'object' || payload === null) {
		return false;
	}

	const record = payload as Record<string, unknown>;
	return (
		typeof record.id === 'string' &&
		typeof record.title === 'string' &&
		isNullableString(record.description) &&
		isNullableString(record.org_id) &&
		isNullableString(record.org_name) &&
		isNullableString(record.license) &&
		isNullableNumber(record.quality_score) &&
		isNullableNumber(record.completeness) &&
		isNullableNumber(record.freshness_days) &&
		Array.isArray(record.resources) &&
		record.resources.every(isResourceContract) &&
		isDatasetStructureContract(record.dataset_structure)
	);
}