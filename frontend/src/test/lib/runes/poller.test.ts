import { describe, expect, test, vi, beforeEach, afterEach } from 'vitest';
import { usePoll } from '$lib/runes/poller.svelte';

describe('usePoll', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	test('usePoll sets data after successful fetch via refresh', async () => {
		// Arrange
		const fetcher = vi.fn().mockResolvedValue({ hello: 'world' });

		// Act — utiliser refresh() pour déclencher execute() manuellement
		const poll = usePoll(fetcher, { interval: 30_000 });
		await poll.refresh();

		// Assert
		expect(poll.data).toEqual({ hello: 'world' });
		expect(poll.error).toBeNull();
		expect(poll.loading).toBe(false);
	});

	test('usePoll sets error after fetcher rejection via refresh', async () => {
		// Arrange
		const fetcher = vi.fn().mockRejectedValue(new Error('Network failure'));

		// Act
		const poll = usePoll(fetcher, { interval: 30_000 });
		await poll.refresh();

		// Assert
		expect(poll.data).toBeNull();
		expect(poll.error).toBe('Network failure');
		expect(poll.loading).toBe(false);
	});

	test('usePoll sets generic error for non-Error rejections via refresh', async () => {
		// Arrange
		const fetcher = vi.fn().mockRejectedValue('string error');

		// Act
		const poll = usePoll(fetcher, { interval: 30_000 });
		await poll.refresh();

		// Assert
		expect(poll.error).toBe('Erreur inconnue');
	});

	test('usePoll shows loading state while fetcher is pending', async () => {
		// Arrange — ne jamais résoudre pour rester en pending
		const fetcher = vi.fn().mockImplementation(() => new Promise(() => {}));

		// Act
		const poll = usePoll(fetcher, { interval: 30_000 });
		const refreshPromise = poll.refresh();

		// Assert — loading est true pendant l'appel
		expect(poll.loading).toBe(true);
	});

	test('usePoll does not call fetcher when enabled is false', () => {
		// Arrange
		const fetcher = vi.fn().mockResolvedValue('data');

		// Act
		const poll = usePoll(fetcher, { interval: 30_000, enabled: false });

		// Assert
		expect(fetcher).not.toHaveBeenCalled();
		expect(poll.enabled).toBe(false);
	});

	test('usePoll refresh re-executes the fetcher and updates data', async () => {
		// Arrange
		const fetcher = vi
			.fn()
			.mockResolvedValueOnce('first')
			.mockResolvedValueOnce('second');
		const poll = usePoll(fetcher, { interval: 30_000 });
		await poll.refresh();
		expect(poll.data).toBe('first');

		// Act
		await poll.refresh();

		// Assert
		expect(poll.data).toBe('second');
	});

	test('usePoll toggle enabled off then on allows refresh to work', async () => {
		// Arrange
		const fetcher = vi.fn().mockResolvedValue('data');
		const poll = usePoll(fetcher, { interval: 1000 });

		// Act — désactiver
		poll.enabled = false;
		expect(poll.enabled).toBe(false);

		// Act — réactiver puis refresh manuel
		poll.enabled = true;
		await poll.refresh();

		// Assert
		expect(poll.data).toBe('data');
	});

	test('usePoll clear error on retry via refresh', async () => {
		// Arrange
		const fetcher = vi
			.fn()
			.mockRejectedValueOnce(new Error('fail'))
			.mockResolvedValueOnce('recovered');
		const poll = usePoll(fetcher, { interval: 5000 });
		await poll.refresh();
		expect(poll.error).toBe('fail');

		// Act — nouveau refresh
		await poll.refresh();

		// Assert
		expect(poll.error).toBeNull();
		expect(poll.data).toBe('recovered');
	});
});