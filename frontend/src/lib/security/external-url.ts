const ALLOWED_EXTERNAL_PROTOCOLS = new Set(['http:', 'https:']);

export function getSafeExternalUrl(rawUrl: string | null | undefined): string | null {
	if (!rawUrl) {
		return null;
	}

	const trimmed = rawUrl.trim();
	if (trimmed.length === 0) {
		return null;
	}

	try {
		const parsedUrl = new URL(trimmed);
		if (!ALLOWED_EXTERNAL_PROTOCOLS.has(parsedUrl.protocol.toLowerCase())) {
			return null;
		}
		return trimmed;
	} catch {
		return null;
	}
}