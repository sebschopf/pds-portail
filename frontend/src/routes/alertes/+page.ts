import type { PageLoad } from './$types';
import type { WatchersResponse, AlertsResponse } from '$lib/types/watchers';

interface AlertsPageData {
	status: 'loading' | 'success' | 'error' | 'not-authenticated';
	watchers?: WatchersResponse;
	alerts?: AlertsResponse;
	errorMessage?: string;
	token?: string;
}

export const load: PageLoad<AlertsPageData> = async ({ url, fetch }) => {
	const urlToken = url.searchParams.get('token');
	const magicToken = url.searchParams.get('magic');

	// Flux magic link : consommation du lien email (ADR-030)
	if (magicToken) {
		try {
			const consumeRes = await fetch(
				`/api/v1/magic-link/consume?magic=${encodeURIComponent(magicToken)}`
			);

			if (!consumeRes.ok) {
				const errorMessage = 'Le lien email est invalide ou expiré. Demandez un nouveau lien.';
				return { status: 'not-authenticated', errorMessage };
			}

			const consumed = (await consumeRes.json()) as { token: string; watcher_id: string };
			const token: string = consumed.token;

			// Charge les données avec le token permanent récupéré
			const [watchersRes, alertsRes] = await Promise.all([
				fetch(`/api/v1/watchers?token=${encodeURIComponent(token)}`),
				fetch(`/api/v1/alerts?token=${encodeURIComponent(token)}`)
			]);

			if (!watchersRes.ok) {
				return { status: 'error', errorMessage: 'Impossible de charger vos alertes.' };
			}

			const watchersData: WatchersResponse = await watchersRes.json();
			const alertsData: AlertsResponse = alertsRes.ok
				? await alertsRes.json()
				: { watcher_id: consumed.watcher_id, count: 0, items: [] };

			return {
				status: 'success',
				watchers: watchersData,
				alerts: alertsData,
				token
			};
		} catch (error) {
			console.error('Erreur consommation magic link:', error);
			return {
				status: 'error',
				errorMessage: 'Impossible de traiter le lien email. Veuillez réessayer.'
			};
		}
	}

	if (!urlToken) {
		// Le client gérera la récupération depuis localStorage (onMount dans +page.svelte)
		return { status: 'not-authenticated', token: undefined };
	}

	try {
		const token = urlToken;

		const watchersRes = await fetch(`/api/v1/watchers?token=${encodeURIComponent(token)}`);
		if (!watchersRes.ok) {
			if (watchersRes.status === 401 || watchersRes.status === 403) {
				return {
					status: 'not-authenticated',
					token: undefined,
					errorMessage: 'Token invalide'
				};
			}
			throw new Error(`Watchers API error: ${watchersRes.status}`);
		}

		const watchersData: WatchersResponse = await watchersRes.json();

		const alertsRes = await fetch(`/api/v1/alerts?token=${encodeURIComponent(token)}`);
		if (!alertsRes.ok) {
			throw new Error(`Alerts API error: ${alertsRes.status}`);
		}

		const alertsData: AlertsResponse = await alertsRes.json();

		return {
			status: 'success',
			watchers: watchersData,
			alerts: alertsData,
			token
		};
	} catch (error) {
		console.error('Error loading alerts page:', error);
		return {
			status: 'error',
			errorMessage: 'Impossible de charger vos alertes. Veuillez réessayer.',
			token: undefined
		};
	}
};
