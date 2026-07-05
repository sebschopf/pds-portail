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
	// Get token from URL or we'll let the client handle localStorage
	const urlToken = url.searchParams.get('token');

	if (!urlToken) {
		// Client will check localStorage
		return {
			status: 'not-authenticated',
			token: undefined
		};
	}

	try {
		// If we have a token, try to load the data server-side
		const token = urlToken;

		// Fetch watcher data
		const watchersRes = await fetch(`/api/v1/watchers?token=${encodeURIComponent(token)}`);
		if (!watchersRes.ok) {
			if (watchersRes.status === 401 || watchersRes.status === 403) {
				return {
					status: 'not-authenticated',
					token: undefined,
					errorMessage: 'Token invalide ou expiré'
				};
			}
			throw new Error(`Watchers API error: ${watchersRes.status}`);
		}

		const watchersData: WatchersResponse = await watchersRes.json();

		// Fetch alerts history
		const alertsRes = await fetch(`/api/v1/alerts?token=${encodeURIComponent(token)}`);
		if (!alertsRes.ok) {
			throw new Error(`Alerts API error: ${alertsRes.status}`);
		}

		const alertsData: AlertsResponse = await alertsRes.json();

		return {
			status: 'success',
			watchers: watchersData,
			alerts: alertsData,
			token: token
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
