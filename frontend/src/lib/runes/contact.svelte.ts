/**
 * Rune de formulaire de contact — encapsule l'état et l'envoi.
 *
 * Usage dans +page.svelte :
 *   const form = useContactForm();
 */
export function useContactForm() {
	let concerne = $state('surveillance');
	let email = $state('');
	let message = $state('');
	let loading = $state(false);
	let sent = $state(false);
	let error = $state<string | null>(null);

	async function handleSubmit(e: Event) {
		e.preventDefault();
		loading = true;
		error = null;
		try {
			const res = await fetch('/api/v1/contact', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ concerne, email, message })
			});
			if (res.ok) {
				sent = true;
			} else {
				error = 'Une erreur est survenue. Veuillez réessayer.';
			}
		} catch {
			error = 'Erreur de connexion. Veuillez réessayer.';
		} finally {
			loading = false;
		}
	}

	return {
		get concerne() {
			return concerne;
		},
		set concerne(v: string) {
			concerne = v;
		},
		get email() {
			return email;
		},
		set email(v: string) {
			email = v;
		},
		get message() {
			return message;
		},
		set message(v: string) {
			message = v;
		},
		get loading() {
			return loading;
		},
		get sent() {
			return sent;
		},
		get error() {
			return error;
		},
		handleSubmit
	};
}