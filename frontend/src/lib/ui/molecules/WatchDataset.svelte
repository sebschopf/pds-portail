<script lang="ts">
	import { Button, Input, Modal } from '$lib';
	import { onMount } from 'svelte';
	import type { WatchDatasetState } from '$lib/types/watchers';

	let {
		dataset_id,
		dataset_title,
		polar_product_id,
		polar_checkout_url
	}: {
		dataset_id: string;
		dataset_title: string;
		polar_product_id?: string; // Legacy mode: product_xxx
		polar_checkout_url?: string; // Preferred mode: https://buy.polar.sh/...
	} = $props();

	let watchState: WatchDatasetState = $state('idle');
	let email = $state('');
	let error = $state<string | null>(null);
	let modalOpen = $state(false);
	let isWatched = $state(false);

	const POLAR_CHECKOUT_BASE = 'https://buy.polar.sh';
	const storageKey = $derived(`pds-watcher-${dataset_id}`);

	// Polar product ID should be configured per environment
	// Format: product_xxxxxxxxxxxx

	onMount(() => {
		// Check if this dataset is being watched (token in localStorage)
		const token = localStorage.getItem(storageKey);
		if (token) {
			isWatched = true;
			watchState = 'active';
		}
	});

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

		if (!polar_product_id && !polar_checkout_url) {
			error = 'Service de paiement indisponible. Veuillez réessayer plus tard.';
			watchState = 'error';
			return;
		}

		watchState = 'pending';
		error = null;

		// Mode hébergé (checkout link) : redirection vers l'URL telle quelle.
		// Polar gère l'email, les métadonnées et la redirection via le dashboard.
		// Mode legacy (productId) : fallback avec query params.
		if (polar_checkout_url) {
			window.location.href = polar_checkout_url;
			return;
		}

		const checkoutUrl = new URL(`${POLAR_CHECKOUT_BASE}/checkout`);
		if (polar_product_id) {
			checkoutUrl.searchParams.set('productId', polar_product_id);
		}
		checkoutUrl.searchParams.set('customerEmail', email);
		checkoutUrl.searchParams.set('customerName', '');
		checkoutUrl.searchParams.set('metadata[dataset_id]', dataset_id);
		checkoutUrl.searchParams.set('metadata[dataset_title]', dataset_title);

		window.location.href = checkoutUrl.toString();
	}

	function handleRemoveWatch() {
		if (confirm(`Êtes-vous sûr d'arrêter la surveillance de "${dataset_title}" ?`)) {
			watchState = 'pending';
			// Token from localStorage is used to call DELETE endpoint
			const token = localStorage.getItem(storageKey);
			if (token) {
				fetch(`/api/v1/watchers/${dataset_id}?token=${encodeURIComponent(token)}`, {
					method: 'DELETE'
				})
					.then((res) => {
						if (res.ok) {
							localStorage.removeItem(storageKey);
						isWatched = false;
						watchState = 'idle';
					} else {
						error = 'Impossible d\'arrêter la surveillance.';
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
	}
</script>

<div class="watch-dataset">
	{#if watchState === 'active'}
		<div class="watched-badge" role="status" aria-label="Ce dataset est surveillé">
			<span class="badge-icon" aria-hidden="true">✓</span>
			<span class="badge-text">Surveillé</span>
			<button class="unwatch-btn" onclick={handleRemoveWatch} aria-label="Arrêter la surveillance">
				Arrêter
			</button>
		</div>
	{:else if watchState === 'idle' || watchState === 'error'}
		<Button
			label="Surveiller ce dataset"
			variant="primary"
			onclick={openModal}
			disabled={!polar_product_id && !polar_checkout_url}
		/>
		{#if watchState === 'error' && error}
			<p class="error-message" role="alert">{error}</p>
		{/if}
	{:else if watchState === 'pending'}
		<div class="pending-state">
			<span class="spinner" aria-hidden="true"></span>
			<span>Traitement en cours...</span>
		</div>
	{/if}

	<Modal title="Surveiller ce dataset" open={modalOpen} onclose={closeModal}>
		{#snippet children()}
			<div class="modal-content">
				<h3 class="modal-title">Surveillance de dataset</h3>
				<p class="modal-description">
					Recevez une alerte par email à chaque changement détecté sur <strong>{dataset_title}</strong>.
				</p>
				<p class="modal-price">5 CHF/mois</p>

				<div class="form-group">
					<Input
						id="email-input"
						label="Votre adresse email"
						type="email"
						placeholder="vous@exemple.ch"
						bind:value={email}
						disabled={watchState === 'pending'}
					/>
				</div>

				{#if error}
					<p class="error-message" role="alert">{error}</p>
				{/if}

				<div class="form-actions">
					<Button
				label={watchState === 'pending' ? 'Redirection vers Polar...' : 'Procéder au paiement'}
				variant="primary"
					disabled={watchState === 'pending' || !email || (!polar_product_id && !polar_checkout_url)}
						onclick={handlePolarCheckout}
					/>
					<button class="cancel-btn" onclick={closeModal} disabled={watchState === 'pending'}>
						Annuler
					</button>
				</div>

				<p class="modal-note">
					Vous serez redirigé vers Polar pour finaliser votre paiement en toute sécurité. PDS-Portail ne stocke jamais vos données bancaires.
				</p>
			</div>
		{/snippet}
	</Modal>
</div>

<style>
	.watch-dataset {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.watched-badge {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: var(--color-success-subtle);
		border: 1px solid var(--color-success);
		border-radius: var(--radius-none);
		font-size: clamp(0.75rem, 0.9rem, 1rem);
		color: var(--color-on-surface);
	}

	.badge-icon {
		color: var(--color-success);
		font-weight: 700;
		font-size: var(--font-size-heading-md);
	}

	.badge-text {
		flex: 1;
		font-weight: 500;
	}

	.unwatch-btn {
		padding: var(--space-1) var(--space-2);
		background: transparent;
		border: 1px solid var(--color-on-surface);
		border-radius: var(--radius-none);
		font-size: clamp(0.75rem, 0.85rem, 1rem);
		cursor: pointer;
		transition: background-color 140ms ease, color 140ms ease;
	}

	.unwatch-btn:hover {
		background: var(--color-on-surface);
		color: var(--color-surface);
	}

	.unwatch-btn:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	.error-message {
		padding: var(--space-2) var(--space-3);
		background: var(--color-error-subtle);
		border-left: 3px solid var(--color-error);
		color: var(--color-on-surface);
		font-size: clamp(0.75rem, 0.9rem, 1rem);
		margin: 0;
		border-radius: var(--radius-none);
	}

	.pending-state {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3);
		color: var(--color-on-surface-muted);
	}

	.spinner {
		display: inline-block;
		width: 18px;
		height: 18px;
		border: 2px solid var(--color-border);
		border-top-color: var(--color-primary);
		border-radius: var(--radius-none);
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.modal-content {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.modal-title {
		margin: 0;
		font-size: clamp(1.1rem, 1.25rem, 1.5rem);
		font-weight: 700;
	}

	.modal-description {
		margin: 0;
		color: var(--color-on-surface-secondary);
		line-height: var(--line-height-relaxed);
	}

	.modal-price {
		margin: 0;
		font-size: var(--font-size-display-metric);
		font-weight: 700;
		color: var(--color-primary);
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.form-actions {
		display: flex;
		gap: var(--space-2);
	}

	.cancel-btn {
		flex: 1;
		padding: var(--space-3) var(--space-4);
		background: var(--color-surface-muted);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		font-weight: 500;
		cursor: pointer;
		transition: background-color 140ms ease;
	}

	.cancel-btn:hover:not(:disabled) {
		background: var(--color-surface);
	}

	.cancel-btn:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	.cancel-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.modal-note {
		margin: 0;
		padding: var(--space-2) var(--space-3);
		background: var(--color-surface-muted);
		border-radius: var(--radius-none);
		font-size: clamp(0.75rem, 0.85rem, 1rem);
		color: var(--color-on-surface-muted);
		line-height: var(--line-height-relaxed);
	}
</style>
