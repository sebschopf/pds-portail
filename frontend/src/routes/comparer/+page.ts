import type { PageLoad } from './$types';
import type { CompareItem, CompareResponse } from '$lib/types/compare';

type ComparePageData = {
	error: string | null;
	items: CompareItem[];
};

/**
 * Loader pour la page /comparer — appelle POST /api/v1/compare.
 * Lit les IDs depuis ?ids=id1,id2,id3 et les transmet au backend.
 */
export const load: PageLoad<ComparePageData> = async ({ url, fetch }) => {
	const rawIds = url.searchParams.get('ids') ?? '';
	const ids: string[] = rawIds
		.split(',')
		.map((id: string) => id.trim())
		.filter((id: string) => id.length > 0);

	if (ids.length < 2) {
		return {
			error: "Au moins 2 datasets sont necessaires pour une comparaison.",
			items: [],
		};
	}

	if (ids.length > 4) {
		return {
			error: "Maximum 4 datasets comparables (les 4 premiers seront conserves).",
			items: [],
		};
	}

	try {
		const response = await fetch('/api/v1/compare', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ ids }),
		});

		if (!response.ok) {
			const detail = await response.text();
			return {
				error: `Erreur lors de la comparaison: ${detail || response.statusText}`,
				items: [],
			};
		}

		const data: CompareResponse = await response.json();
		return {
			error: null,
			items: data.items,
		};
	} catch (err) {
		return {
			error: `Erreur reseau: ${err instanceof Error ? err.message : 'inconnue'}`,
			items: [],
		};
	}
};