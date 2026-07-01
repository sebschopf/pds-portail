const SEARCH_CONTEXT_KEYS = ['q', 'sort', 'page', 'org', 'fmt'] as const;

function isPositivePage(value: string): boolean {
	const page = Number.parseInt(value, 10);
	return Number.isFinite(page) && page > 0;
}

export function normalizeSearchContext(rawContext: string | null | undefined): string | null {
	if (!rawContext) {
		return null;
	}

	const source = rawContext.startsWith('?') ? rawContext.slice(1) : rawContext;
	const sourceParams = new URLSearchParams(source);
	const normalized = new URLSearchParams();

	for (const key of SEARCH_CONTEXT_KEYS) {
		const value = sourceParams.get(key);
		if (!value) {
			continue;
		}

		if (key === 'page' && !isPositivePage(value)) {
			continue;
		}

		normalized.set(key, value);
	}

	const csvTags = (sourceParams.get('tags') ?? '')
		.split(',')
		.map((tag) => tag.trim())
		.filter((tag) => tag.length > 0);

	if (csvTags.length > 0) {
		normalized.set('tags', Array.from(new Set(csvTags)).join(','));
	} else {
		const legacyTags = Array.from(
			new Set(
				sourceParams
					.getAll('tag')
					.map((tag) => tag.trim())
					.filter((tag) => tag.length > 0)
			)
		);

		for (const tag of legacyTags) {
			normalized.append('tag', tag);
		}
	}

	const normalizedValue = normalized.toString();
	return normalizedValue.length > 0 ? normalizedValue : null;
}

export function buildSearchHref(searchContext: string | null | undefined): string {
	const normalized = normalizeSearchContext(searchContext);
	return normalized ? `/?${normalized}` : '/';
}

export function appendSearchContext(path: string, searchContext: string | null | undefined): string {
	const normalized = normalizeSearchContext(searchContext);
	if (!normalized) {
		return path;
	}

	const separator = path.includes('?') ? '&' : '?';
	return `${path}${separator}ctx=${encodeURIComponent(normalized)}`;
}