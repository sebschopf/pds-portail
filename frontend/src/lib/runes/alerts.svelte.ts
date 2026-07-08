import type { PageData } from '../../routes/alertes/$types';

/**
 * Rune de gestion des alertes — encapsule la logique magic link,
 * suppression de surveillance, et token localStorage.
 *
 * Usage dans +page.svelte :
 *   const alerts = useAlerts(data);
 *   onMount(() => alerts.initTokens());
 */
export function useAlerts(getData: () => PageData) {
	// --- Magic link ---
	let magicLinkEmail = $state('');
	let magicLinkLoading = $state(false);
	let magicLinkMessage = $state<string | null>(null);
	let unsubscribeError = $state<string | null>(null);

	// --- Dérivés ---
	let isAuthenticated = $derived(getData().status === 'success');
	let watcherStatus = $derived(getData().watchers?.status ?? null);
	let pageTitle = $derived(
		isAuthenticated ? 'Mes alertes - PDS Portail' : 'Alertes datasets - PDS Portail'
	);

	// --- Helpers localStorage ---
	function storeWatcherTokens(token: string, datasetIds: string[]) {
		localStorage.setItem('pds-watcher-token', token);
		for (const datasetId of datasetIds) {
			localStorage.setItem(`pds-watcher-${datasetId}`, token);
		}
	}

	function findStoredWatcherToken(): string | null {
		const directToken = localStorage.getItem('pds-watcher-token');
		if (directToken) return directToken;
		for (let i = 0; i < localStorage.length; i++) {
			const key = localStorage.key(i);
			if (key?.startsWith('pds-watcher-')) {
				const token = localStorage.getItem(key);
				if (token) return token;
			}
		}
		return null;
	}

	function initTokens() {
		const d = getData();
		if (d.status === 'success' && d.token && d.watchers?.items) {
			storeWatcherTokens(d.token, d.watchers.items.map((item) => item.dataset_id));
			return;
		}
		if (d.status === 'not-authenticated') {
			const storedToken = findStoredWatcherToken();
			if (storedToken) {
				window.location.href = `/alertes?token=${encodeURIComponent(storedToken)}`;
			}
		}
	}

	// --- Actions ---
	async function handleRequestMagicLink(event: Event) {
		event.preventDefault();
		magicLinkLoading = true;
		magicLinkMessage = null;
		try {
			const res = await fetch('/api/v1/magic-link', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email: magicLinkEmail })
			});
			if (res.ok) {
				magicLinkMessage = `Un lien d'accès a été envoyé à ${magicLinkEmail}. Vérifiez votre boîte email (validité 15 minutes).`;
				magicLinkEmail = '';
			} else {
				magicLinkMessage = 'Une erreur est survenue. Veuillez réessayer.';
			}
		} catch (err) {
			console.error('Magic link request error:', err);
			magicLinkMessage = 'Erreur de connexion. Veuillez réessayer.';
		} finally {
			magicLinkLoading = false;
		}
	}

	async function handleRemoveWatch(watchedDatasetId: string, datasetTitle: string) {
		if (!confirm(`Êtes-vous sûr d'arrêter la surveillance de "${datasetTitle}" ?`)) return;
		try {
			const res = await fetch(
				`/api/v1/watchers/${watchedDatasetId}?token=${encodeURIComponent(getData().token || '')}`,
				{ method: 'DELETE' }
			);
			if (res.ok) {
				window.location.reload();
			} else {
				unsubscribeError = "Impossible d'arrêter la surveillance.";
			}
		} catch (err) {
			console.error('Remove watch error:', err);
			unsubscribeError = 'Erreur de connexion.';
		}
	}

	return {
		// État magic link
		get magicLinkEmail() {
			return magicLinkEmail;
		},
		set magicLinkEmail(v: string) {
			magicLinkEmail = v;
		},
		get magicLinkLoading() {
			return magicLinkLoading;
		},
		get magicLinkMessage() {
			return magicLinkMessage;
		},
		get unsubscribeError() {
			return unsubscribeError;
		},
		// Dérivés
		get isAuthenticated() {
			return isAuthenticated;
		},
		get watcherStatus() {
			return watcherStatus;
		},
		get pageTitle() {
			return pageTitle;
		},
		// Actions
		handleRequestMagicLink,
		handleRemoveWatch,
		initTokens
	};
}