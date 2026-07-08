import { describe, expect, test, vi, beforeEach } from 'vitest';
import { useAlerts } from '$lib/runes/alerts.svelte';

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
const mockLocationHref = vi.fn();
const mockWindowReload = vi.fn();
const mockWindow = {
	location: {
		get href(): string {
			return '';
		},
		set href(v: string) {
			mockLocationHref(v);
		},
		reload: mockWindowReload
	}
} as unknown as Window & typeof globalThis;
Object.defineProperty(globalThis, 'window', {
	value: mockWindow,
	writable: true
});

// --- Types ---
type PageDataInput = {
	status: 'success' | 'not-authenticated' | 'error';
	errorMessage?: string;
	token?: string;
	watchers?: {
		watcher_id: string;
		email: string;
		status: string;
		items: { id: string; dataset_id: string; dataset_title: string | null; created_at: string }[];
	};
	alerts?: {
		watcher_id: string;
		count: number;
		items: {
			id: string;
			dataset_id: string;
			dataset_title: string | null;
			change_type: string;
			previous_value: string | null;
			new_value: string | null;
			detected_at: string;
			notified_at: string | null;
		}[];
	};
};

// --- Helpers ---
function makeData(overrides: Partial<PageDataInput> = {}): () => any {
	return (): any => ({
		status: 'not-authenticated' as const,
		errorMessage: undefined as string | undefined,
		token: undefined as string | undefined,
		watchers: undefined as
			| {
					watcher_id: string;
					email: string;
					status: string;
					items: { id: string; dataset_id: string; dataset_title: string | null; created_at: string }[];
			  }
			| undefined,
		alerts: undefined as
			| {
					watcher_id: string;
					count: number;
					items: {
						id: string;
						dataset_id: string;
						dataset_title: string | null;
						change_type: string;
						previous_value: string | null;
						new_value: string | null;
						detected_at: string;
						notified_at: string | null;
					}[];
			  }
			| undefined,
		...overrides
	});
}

describe('useAlerts', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		localStorageStore.clear();
		vi.spyOn(console, 'error').mockImplementation(() => {});
	});

	// --- Derived state ---
	test('useAlerts isAuthenticated est true quand status est success', () => {
		const alerts = useAlerts(makeData({ status: 'success' }));
		expect(alerts.isAuthenticated).toBe(true);
	});

	test('useAlerts isAuthenticated est false quand status est not-authenticated', () => {
		const alerts = useAlerts(makeData({ status: 'not-authenticated' }));
		expect(alerts.isAuthenticated).toBe(false);
	});

	test('useAlerts watcherStatus reflète le statut du watcher', () => {
		const alerts = useAlerts(
			makeData({
				status: 'success',
				watchers: {
					watcher_id: 'w-1',
					email: 'x@x.ch',
					status: 'suspended',
					items: []
				}
			})
		);
		expect(alerts.watcherStatus).toBe('suspended');
	});

	test('useAlerts watcherStatus est null sans watcher', () => {
		const alerts = useAlerts(makeData({ status: 'success' }));
		expect(alerts.watcherStatus).toBeNull();
	});

	test('useAlerts pageTitle affiche "Mes alertes" quand authentifié', () => {
		const alerts = useAlerts(makeData({ status: 'success' }));
		expect(alerts.pageTitle).toBe('Mes alertes - PDS Portail');
	});

	test('useAlerts pageTitle affiche "Alertes datasets" quand non authentifié', () => {
		const alerts = useAlerts(makeData({ status: 'not-authenticated' }));
		expect(alerts.pageTitle).toBe('Alertes datasets - PDS Portail');
	});

	// --- initTokens: success path ---
	test('useAlerts initTokens stocke les tokens quand status=success', () => {
		const alerts = useAlerts(
			makeData({
				status: 'success',
				token: 'tok-abc',
				watchers: {
					watcher_id: 'w-1',
					email: 'x@x.ch',
					status: 'active',
					items: [
						{ id: 'wi-1', dataset_id: 'ds-a', dataset_title: 'DS A', created_at: '' },
						{ id: 'wi-2', dataset_id: 'ds-b', dataset_title: 'DS B', created_at: '' }
					]
				}
			})
		);

		alerts.initTokens();

		expect(mockLocalStorage.setItem).toHaveBeenCalledWith('pds-watcher-token', 'tok-abc');
		expect(mockLocalStorage.setItem).toHaveBeenCalledWith('pds-watcher-ds-a', 'tok-abc');
		expect(mockLocalStorage.setItem).toHaveBeenCalledWith('pds-watcher-ds-b', 'tok-abc');
	});

	// --- initTokens: stored token redirect ---
	test("useAlerts initTokens redirige vers /alertes?token quand pas d'auth mais token stocké", () => {
		localStorageStore.set('pds-watcher-token', 'stored-tok');

		const alerts = useAlerts(makeData({ status: 'not-authenticated' }));
		alerts.initTokens();

		expect(mockLocationHref).toHaveBeenCalledWith('/alertes?token=stored-tok');
	});

	test("useAlerts initTokens trouve le token par prefix pds-watcher- quand pas de token direct", () => {
		localStorageStore.set('pds-watcher-ds-xyz', 'found-tok');

		const alerts = useAlerts(makeData({ status: 'not-authenticated' }));
		alerts.initTokens();

		expect(mockLocationHref).toHaveBeenCalledWith('/alertes?token=found-tok');
	});

	// --- initTokens: nothing to do ---
	test("useAlerts initTokens ne fait rien quand pas d'auth et pas de token stocké", () => {
		const alerts = useAlerts(makeData({ status: 'not-authenticated' }));
		alerts.initTokens();

		expect(mockLocationHref).not.toHaveBeenCalled();
		expect(mockLocalStorage.setItem).not.toHaveBeenCalled();
	});

	// --- handleRequestMagicLink ---
	test('useAlerts handleRequestMagicLink envoie le magic link et affiche le message de succès', async () => {
		mockFetch.mockResolvedValueOnce({ ok: true });
		const alerts = useAlerts(makeData());
		alerts.magicLinkEmail = 'user@example.com';

		await alerts.handleRequestMagicLink(new Event('submit'));

		expect(mockFetch).toHaveBeenCalledWith(
			'/api/v1/magic-link',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ email: 'user@example.com' })
			})
		);
		expect(alerts.magicLinkMessage).toContain('Un lien');
		expect(alerts.magicLinkEmail).toBe('');
		expect(alerts.magicLinkLoading).toBe(false);
		expect(mockFetch).toHaveBeenCalledTimes(1);
	});

	test('useAlerts handleRequestMagicLink affiche une erreur quand la réponse est ko', async () => {
		mockFetch.mockResolvedValueOnce({ ok: false });
		const alerts = useAlerts(makeData());
		alerts.magicLinkEmail = 'bad@example.com';

		await alerts.handleRequestMagicLink(new Event('submit'));

		expect(alerts.magicLinkMessage).toBe('Une erreur est survenue. Veuillez réessayer.');
	});

	test('useAlerts handleRequestMagicLink affiche une erreur de connexion quand fetch lève', async () => {
		mockFetch.mockRejectedValueOnce(new Error('network'));
		const alerts = useAlerts(makeData());
		alerts.magicLinkEmail = 'x@x.ch';

		await alerts.handleRequestMagicLink(new Event('submit'));

		expect(alerts.magicLinkMessage).toBe('Erreur de connexion. Veuillez réessayer.');
	});

	// --- handleRemoveWatch ---
	test('useAlerts handleRemoveWatch supprime une surveillance avec succès', async () => {
		(globalThis.confirm as ReturnType<typeof vi.fn>).mockReturnValueOnce(true);
		mockFetch.mockResolvedValueOnce({ ok: true });
		const alerts = useAlerts(
			makeData({ status: 'success', token: 'tok-del' })
		);

		await alerts.handleRemoveWatch('w-1', 'Mon Dataset');

		expect(mockWindowReload).toHaveBeenCalled();
	});

	test("useAlerts handleRemoveWatch ne fait rien si l'utilisateur refuse", async () => {
		(globalThis.confirm as ReturnType<typeof vi.fn>).mockReturnValueOnce(false);
		const alerts = useAlerts(makeData({ status: 'success', token: 'tok' }));

		await alerts.handleRemoveWatch('w-1', 'Mon Dataset');

		expect(mockFetch).not.toHaveBeenCalled();
	});

	test('useAlerts handleRemoveWatch définit unsubscribeError quand le serveur répond ko', async () => {
		(globalThis.confirm as ReturnType<typeof vi.fn>).mockReturnValueOnce(true);
		mockFetch.mockResolvedValueOnce({ ok: false });
		const alerts = useAlerts(
			makeData({ status: 'success', token: 'tok' })
		);

		await alerts.handleRemoveWatch('w-1', 'Mon Dataset');

		expect(alerts.unsubscribeError).toBe("Impossible d'arrêter la surveillance.");
	});

	test('useAlerts handleRemoveWatch définit unsubscribeError en cas de rejet fetch', async () => {
		(globalThis.confirm as ReturnType<typeof vi.fn>).mockReturnValueOnce(true);
		mockFetch.mockRejectedValueOnce(new Error('offline'));
		const alerts = useAlerts(
			makeData({ status: 'success', token: 'tok' })
		);

		await alerts.handleRemoveWatch('w-1', 'Mon Dataset');

		expect(alerts.unsubscribeError).toBe('Erreur de connexion.');
	});

	// --- magic link loading state ---
	test('useAlerts handleRequestMagicLink passe loading=true puis false', async () => {
		mockFetch.mockResolvedValueOnce({ ok: true });
		const alerts = useAlerts(makeData());
		alerts.magicLinkEmail = 'x@x.ch';

		const promise = alerts.handleRequestMagicLink(new Event('submit'));
		expect(alerts.magicLinkLoading).toBe(true);

		await promise;
		expect(alerts.magicLinkLoading).toBe(false);
	});
});