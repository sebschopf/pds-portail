import { describe, expect, test, vi, beforeEach } from 'vitest';
import { useWatchDataset } from '$lib/runes/watcher.svelte';

// --- Mock globals ---
globalThis.confirm = vi.fn();
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

// --- Mock localStorage ---
const localStorageStore = new Map<string, string>();
const mockLocalStorage = {
	getItem: vi.fn((key: string) => localStorageStore.get(key) ?? null),
	setItem: vi.fn((key: string, value: string) => {
		localStorageStore.set(key, value);
	}),
	removeItem: vi.fn((key: string) => {
		localStorageStore.delete(key);
	}),
	key: vi.fn((index: number) => {
		const keys = Array.from(localStorageStore.keys());
		return keys[index] ?? null;
	}),
	get length() {
		return localStorageStore.size;
	},
	clear: vi.fn(() => {
		localStorageStore.clear();
	})
};
Object.defineProperty(globalThis, 'localStorage', {
	value: mockLocalStorage,
	writable: true
});

// --- Mock window.location ---
const mockLocationAssign = vi.fn();
const mockWindow = {
	location: {
		get href(): string {
			return '';
		},
		set href(v: string) {
			mockLocationAssign(v);
		}
	}
} as unknown as Window & typeof globalThis;
Object.defineProperty(globalThis, 'window', {
	value: mockWindow,
	writable: true
});

// --- Helpers ---
const defaultProps = {
	dataset_id: 'ds-1',
	dataset_title: 'Test Dataset',
	polar_product_id: undefined as string | undefined,
	polar_checkout_url: undefined as string | undefined
};

function makeProps(overrides: Partial<typeof defaultProps> = {}) {
	return () => ({ ...defaultProps, ...overrides });
}

describe('useWatchDataset', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		localStorageStore.clear();
		vi.spyOn(console, 'error').mockImplementation(() => {});
	});

	// --- État initial ---
	test('useWatchDataset initialise avec watchState idle', () => {
		const watch = useWatchDataset(makeProps());
		expect(watch.watchState).toBe('idle');
		expect(watch.email).toBe('');
		expect(watch.error).toBeNull();
		expect(watch.modalOpen).toBe(false);
		expect(watch.isWatched).toBe(false);
	});

	// --- init: pas de token → reste idle ---
	test("useWatchDataset init reste idle quand aucun token n'est stocké", () => {
		const watch = useWatchDataset(makeProps());
		watch.init();
		expect(watch.watchState).toBe('idle');
		expect(watch.isWatched).toBe(false);
	});

	// --- init: token stocké → active ---
	test('useWatchDataset init détecte un token stocké et passe en active', () => {
		localStorageStore.set('pds-watcher-ds-1', 'tok-active');
		const watch = useWatchDataset(makeProps());
		watch.init();
		expect(watch.watchState).toBe('active');
		expect(watch.isWatched).toBe(true);
	});

	// --- openModal / closeModal ---
	test('useWatchDataset openModal passe watchState à modal et vide email/error', () => {
		const watch = useWatchDataset(makeProps());
		watch.email = 'old@test.ch';
		watch.modalOpen = false;

		watch.openModal();

		expect(watch.watchState).toBe('modal');
		expect(watch.modalOpen).toBe(true);
		expect(watch.email).toBe('');
		expect(watch.error).toBeNull();
	});

	test('useWatchDataset closeModal ramène watchState à idle depuis modal', () => {
		const watch = useWatchDataset(makeProps());
		watch.openModal();
		expect(watch.watchState).toBe('modal');

		watch.closeModal();

		expect(watch.modalOpen).toBe(false);
		expect(watch.watchState).toBe('idle');
	});

	test('useWatchDataset closeModal ne change pas watchState depuis active', () => {
		localStorageStore.set('pds-watcher-ds-1', 'tok');
		const watch = useWatchDataset(makeProps());
		watch.init();
		expect(watch.watchState).toBe('active');

		watch.closeModal();

		expect(watch.modalOpen).toBe(false);
		expect(watch.watchState).toBe('active');
	});

	// --- handlePolarCheckout: email invalide ---
	test('useWatchDataset handlePolarCheckout définit error pour email invalide', () => {
		const watch = useWatchDataset(makeProps());
		watch.email = 'not-an-email';

		watch.handlePolarCheckout();

		expect(watch.error).toBe('Veuillez entrer une adresse email valide.');
		expect(watch.watchState).toBe('idle');
	});

	test('useWatchDataset handlePolarCheckout définit error pour email vide', () => {
		const watch = useWatchDataset(makeProps());
		watch.email = '';

		watch.handlePolarCheckout();

		expect(watch.error).toBe('Veuillez entrer une adresse email valide.');
	});

	// --- handlePolarCheckout: pas de produit ni checkout_url → indisponible ---
	test('useWatchDataset handlePolarCheckout met watchState=error quand pas de produit ni checkout_url', () => {
		const watch = useWatchDataset(makeProps());
		watch.email = 'test@example.ch';

		watch.handlePolarCheckout();

		expect(watch.error).toBe('Service de paiement indisponible. Veuillez réessayer plus tard.');
		expect(watch.watchState).toBe('error');
	});

	// --- handlePolarCheckout: avec polar_checkout_url ---
	test('useWatchDataset handlePolarCheckout redirige vers le checkout_url avec customer_email', () => {
		const watch = useWatchDataset(
			makeProps({
				polar_checkout_url: 'https://buy.example.com/order'
			})
		);
		watch.email = 'user@example.ch';

		watch.handlePolarCheckout();

		expect(watch.watchState).toBe('pending');
		expect(watch.error).toBeNull();
		expect(mockLocationAssign).toHaveBeenCalledWith(
			expect.stringContaining('https://buy.example.com/order?customer_email=user%40example.ch')
		);
	});

	// --- handlePolarCheckout: avec polar_product_id ---
	test('useWatchDataset handlePolarCheckout redirige vers Polar avec productId', () => {
		const watch = useWatchDataset(
			makeProps({
				polar_product_id: 'prod-42'
			})
		);
		watch.email = 'user@example.ch';

		watch.handlePolarCheckout();

		expect(watch.watchState).toBe('pending');
		expect(watch.error).toBeNull();
		expect(mockLocationAssign).toHaveBeenCalledWith(
			expect.stringContaining('https://buy.polar.sh/checkout')
		);
		expect(mockLocationAssign).toHaveBeenCalledWith(
			expect.stringContaining('productId=prod-42')
		);
		expect(mockLocationAssign).toHaveBeenCalledWith(
			expect.stringContaining('customerEmail=user%40example.ch')
		);
	});

	// --- handleRemoveWatch: succès ---
	test('useWatchDataset handleRemoveWatch supprime la surveillance avec succès', async () => {
		(globalThis.confirm as ReturnType<typeof vi.fn>).mockReturnValueOnce(true);
		mockFetch.mockResolvedValueOnce({ ok: true });
		localStorageStore.set('pds-watcher-ds-1', 'tok-rem');
		const watch = useWatchDataset(makeProps());
		watch.init();
		expect(watch.isWatched).toBe(true);

		watch.handleRemoveWatch();
		await new Promise((r) => setTimeout(r, 0));

		expect(watch.watchState).toBe('idle');
		expect(watch.isWatched).toBe(false);
		expect(localStorageStore.has('pds-watcher-ds-1')).toBe(false);
	});

	// --- handleRemoveWatch: refus utilisateur ---
	test("useWatchDataset handleRemoveWatch ne fait rien si l'utilisateur refuse", () => {
		(globalThis.confirm as ReturnType<typeof vi.fn>).mockReturnValueOnce(false);
		const watch = useWatchDataset(makeProps());

		watch.handleRemoveWatch();

		expect(mockFetch).not.toHaveBeenCalled();
		expect(watch.watchState).not.toBe('pending');
	});

	// --- handleRemoveWatch: échec serveur ---
	test('useWatchDataset handleRemoveWatch définit error quand le serveur répond ko', async () => {
		(globalThis.confirm as ReturnType<typeof vi.fn>).mockReturnValueOnce(true);
		mockFetch.mockResolvedValueOnce({ ok: false });
		localStorageStore.set('pds-watcher-ds-1', 'tok');
		const watch = useWatchDataset(makeProps());
		watch.init();

		watch.handleRemoveWatch();
		await new Promise((r) => setTimeout(r, 0));

		expect(watch.error).toBe("Impossible d'arrêter la surveillance.");
		expect(watch.watchState).toBe('error');
	});

	// --- handleRemoveWatch: erreur réseau ---
	test('useWatchDataset handleRemoveWatch définit error en cas de rejet réseau', async () => {
		(globalThis.confirm as ReturnType<typeof vi.fn>).mockReturnValueOnce(true);
		mockFetch.mockRejectedValueOnce(new Error('offline'));
		localStorageStore.set('pds-watcher-ds-1', 'tok');
		const watch = useWatchDataset(makeProps());
		watch.init();

		watch.handleRemoveWatch();
		await new Promise((r) => setTimeout(r, 0));

		expect(watch.error).toBe('Erreur de connexion.');
		expect(watch.watchState).toBe('error');
	});

	// --- handleRemoveWatch: sans token localStorage ---
	test("useWatchDataset handleRemoveWatch ne fait pas d'appel DELETE sans token stocké", () => {
		(globalThis.confirm as ReturnType<typeof vi.fn>).mockReturnValueOnce(true);
		const watch = useWatchDataset(makeProps());
		// pas de localStorage.set → token = null

		watch.handleRemoveWatch();

		expect(mockFetch).not.toHaveBeenCalled();
	});

	// --- storageKey dérivé ---
	test('useWatchDataset storageKey est dérivé du dataset_id', () => {
		const watch = useWatchDataset(makeProps({ dataset_id: 'my-id' }));
		expect(watch.storageKey).toBe('pds-watcher-my-id');
	});
});