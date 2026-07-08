/**
 * Rune de polling — relance une fonction async à intervalle régulier.
 *
 * Usage :
 *   const poll = usePoll(() => fetch('/api/status').then(r => r.json()), { interval: 30_000 });
 *
 *   {#if poll.loading} Chargement... {/if}
 *   {#if poll.error} {poll.error} {/if}
 *   {#if poll.data} <pre>{JSON.stringify(poll.data)}</pre> {/if}
 */
export function usePoll<T>(
	fetcher: () => Promise<T>,
	options: { interval: number; enabled?: boolean } = { interval: 30_000 }
) {
	let data = $state<T | null>(null);
	let error = $state<string | null>(null);
	let loading = $state(false);
	let enabled = $state(options.enabled ?? true);

	async function execute() {
		loading = true;
		error = null;
		try {
			data = await fetcher();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Erreur inconnue';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (!enabled) return;
		execute();
		const timer = setInterval(execute, options.interval);
		return () => clearInterval(timer);
	});

	return {
		get data() {
			return data;
		},
		get error() {
			return error;
		},
		get loading() {
			return loading;
		},
		get enabled() {
			return enabled;
		},
		set enabled(v: boolean) {
			enabled = v;
		},
		refresh: execute
	};
}