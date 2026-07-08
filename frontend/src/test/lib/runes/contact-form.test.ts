import { describe, expect, test, vi, beforeEach } from 'vitest';
import { useContactForm } from '$lib/runes/contact.svelte';

// --- Mock fetch ---
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

describe('useContactForm', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	// --- État initial ---
	test('useContactForm initialise avec des valeurs par défaut correctes', () => {
		// Arrange
		const form = useContactForm();

		// Assert
		expect(form.concerne).toBe('surveillance');
		expect(form.email).toBe('');
		expect(form.message).toBe('');
		expect(form.loading).toBe(false);
		expect(form.sent).toBe(false);
		expect(form.error).toBeNull();
	});

	// --- Setters ---
	test('useContactForm permet de modifier email, message et concerne', () => {
		// Arrange
		const form = useContactForm();

		// Act
		form.email = 'test@example.ch';
		form.message = 'Bonjour, ceci est un test.';
		form.concerne = 'bug';

		// Assert
		expect(form.email).toBe('test@example.ch');
		expect(form.message).toBe('Bonjour, ceci est un test.');
		expect(form.concerne).toBe('bug');
	});

	// --- handleSubmit: succès ---
	test('useContactForm handleSubmit définit sent=true sur réponse ok', async () => {
		// Arrange
		mockFetch.mockResolvedValueOnce({ ok: true });
		const form = useContactForm();
		form.email = 'test@example.ch';
		form.message = 'Hello';

		// Act
		await form.handleSubmit(new Event('submit'));

		// Assert
		expect(form.sent).toBe(true);
		expect(form.loading).toBe(false);
		expect(form.error).toBeNull();
	});

	// --- handleSubmit: échec serveur ---
	test('useContactForm handleSubmit définit error quand la réponse est ko', async () => {
		// Arrange
		mockFetch.mockResolvedValueOnce({ ok: false });
		const form = useContactForm();
		form.email = 'test@example.ch';
		form.message = 'Hello';

		// Act
		await form.handleSubmit(new Event('submit'));

		// Assert
		expect(form.sent).toBe(false);
		expect(form.loading).toBe(false);
		expect(form.error).toBe('Une erreur est survenue. Veuillez réessayer.');
	});

	// --- handleSubmit: erreur réseau ---
	test('useContactForm handleSubmit définit error en cas de rejet réseau', async () => {
		// Arrange
		mockFetch.mockRejectedValueOnce(new Error('Offline'));
		const form = useContactForm();
		form.email = 'test@example.ch';
		form.message = 'Hello';

		// Act
		await form.handleSubmit(new Event('submit'));

		// Assert
		expect(form.sent).toBe(false);
		expect(form.loading).toBe(false);
		expect(form.error).toBe('Erreur de connexion. Veuillez réessayer.');
	});

	// --- handleSubmit: loading state ---
	test('useContactForm handleSubmit passe loading=true puis false', async () => {
		// Arrange
		mockFetch.mockResolvedValueOnce({ ok: true });
		const form = useContactForm();
		form.email = 'test@example.ch';
		form.message = 'Hello';

		// Act
		const promise = form.handleSubmit(new Event('submit'));

		// Assert — loading est true pendant l'appel
		expect(form.loading).toBe(true);

		await promise;
		expect(form.loading).toBe(false);
	});

	// --- handleSubmit: nettoie l'erreur précédente ---
	test("useContactForm handleSubmit nettoie l'erreur précédente lors d'un nouvel envoi", async () => {
		// Arrange
		mockFetch.mockRejectedValueOnce(new Error('Offline'));
		const form = useContactForm();
		form.email = 'test@example.ch';
		form.message = 'Hello';

		// Premier envoi → erreur
		await form.handleSubmit(new Event('submit'));
		expect(form.error).not.toBeNull();

		// Act — deuxième envoi, succès cette fois
		mockFetch.mockResolvedValueOnce({ ok: true });
		await form.handleSubmit(new Event('submit'));

		// Assert — l'erreur est nettoyée
		expect(form.error).toBeNull();
		expect(form.sent).toBe(true);
	});

	// --- handleSubmit: envoie les bons champs ---
	test('useContactForm handleSubmit envoie concerne, email et message au backend', async () => {
		// Arrange
		mockFetch.mockResolvedValueOnce({ ok: true });
		const form = useContactForm();
		form.email = 'user@example.ch';
		form.message = 'Un message de test';
		form.concerne = 'bug';

		// Act
		await form.handleSubmit(new Event('submit'));

		// Assert
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/v1/contact',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({
					concerne: 'bug',
					email: 'user@example.ch',
					message: 'Un message de test'
				})
			})
		);
	});
});