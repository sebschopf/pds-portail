import type { WatchDatasetState } from '$lib/types/watchers';

/**
 * Rune de surveillance — encapsule la logique d'abonnement Polar.
 *
 * Usage :
 *   const watch = useWatchDataset({ dataset_id, dataset_title, polar_product_id, polar_checkout_url });
 */
export function useWatchDataset(
	getProps: () => {
		dataset_id: string;
		dataset_title: string;
		polar_product_id?: string;
		polar_checkout_url?: string;
	}
) {
	let watchState: WatchDatasetState = $state('idle');
	let email = $state('');
	let error = $state<string | null>(null);
	let modalOpen = $state(false);
	let isWatched = $state(false);

	const POLAR_CHECKOUT_BASE = 'https://buy.polar.sh';
	const storageKey = $derived(`pds-watcher-${getProps().dataset_id}`);

	function init() {
		const token = localStorage.getItem(storageKey);
		if (token) {
			isWatched = true;
			watchState = 'active';
		}
	}

	function openModal() {
		email = '';
		error = null;
		modalOpen = true;
		watchState = 'modal';
	}

	function closeModal() {
		modalOpen = false;
		if (watchState === 'modal') {
			watchState = 'idle';
		}
	}

	function handlePolarCheckout() {
		if (!email || !email.includes('@')) {
			error = 'Veuillez entrer une adresse email valide.';
			return;
		}

		const p = getProps();
		if (!p.polar_product_id && !p.polar_checkout_url) {
			error = 'Service de paiement indisponible. Veuillez réessayer plus tard.';
			watchState = 'error';
			return;
		}

		watchState = 'pending';
		error = null;

		if (p.polar_checkout_url) {
			const checkoutLink = new URL(p.polar_checkout_url);
			checkoutLink.searchParams.set('customer_email', email);
			checkoutLink.searchParams.set('metadata[dataset_id]', p.dataset_id);
			checkoutLink.searchParams.set('metadata[dataset_title]', p.dataset_title);
			window.location.href = checkoutLink.toString();
			return;
		}

		const checkoutUrl = new URL(`${POLAR_CHECKOUT_BASE}/checkout`);
		if (p.polar_product_id) {
			checkoutUrl.searchParams.set('productId', p.polar_product_id);
		}
		checkoutUrl.searchParams.set('customerEmail', email);
		checkoutUrl.searchParams.set('customerName', '');
		checkoutUrl.searchParams.set('metadata[dataset_id]', p.dataset_id);
		checkoutUrl.searchParams.set('metadata[dataset_title]', p.dataset_title);

		window.location.href = checkoutUrl.toString();
	}

	function handleRemoveWatch() {
		if (!confirm(`Êtes-vous sûr d'arrêter la surveillance de "${getProps().dataset_title}" ?`)) return;

		watchState = 'pending';
		const token = localStorage.getItem(storageKey);
		if (token) {
			fetch(`/api/v1/watchers/${getProps().dataset_id}?token=${encodeURIComponent(token)}`, {
				method: 'DELETE'
			})
				.then((res) => {
					if (res.ok) {
						localStorage.removeItem(storageKey);
						isWatched = false;
						watchState = 'idle';
					} else {
						error = "Impossible d'arrêter la surveillance.";
						watchState = 'error';
					}
				})
				.catch((err) => {
					console.error('Error removing watch:', err);
					error = 'Erreur de connexion.';
					watchState = 'error';
				});
		}
	}

	return {
		get watchState() {
			return watchState;
		},
		get email() {
			return email;
		},
		set email(v: string) {
			email = v;
		},
		get error() {
			return error;
		},
		get modalOpen() {
			return modalOpen;
		},
		set modalOpen(v: boolean) {
			modalOpen = v;
		},
		get isWatched() {
			return isWatched;
		},
		get storageKey() {
			return storageKey;
		},
		init,
		openModal,
		closeModal,
		handlePolarCheckout,
		handleRemoveWatch
	};
}