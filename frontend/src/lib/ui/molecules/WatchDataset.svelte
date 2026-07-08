<script lang="ts">
	import { Button, Input, Modal } from '$lib';
	import { onMount } from 'svelte';
	import { useWatchDataset } from '$lib/runes/watcher.svelte';

	let {
		dataset_id,
		dataset_title,
		polar_product_id,
		polar_checkout_url
	}: {
		dataset_id: string;
		dataset_title: string;
		polar_product_id?: string;
		polar_checkout_url?: string;
	} = $props();

	const watch = useWatchDataset(() => ({ dataset_id, dataset_title, polar_product_id, polar_checkout_url }));

	onMount(() => {
		watch.init();
	});
</script>

<div class="watch-dataset">
	{#if watch.watchState === 'active'}
		<div class="watched-badge" role="status" aria-label="Ce dataset est surveillé">
			<span class="badge-icon" aria-hidden="true">✓</span>
			<span class="badge-text">Surveillé</span>
			<button class="unwatch-btn" onclick={watch.handleRemoveWatch} aria-label="Arrêter la surveillance">
				Arrêter
			</button>
		</div>
	{:else if watch.watchState === 'idle' || watch.watchState === 'error'}
		<Button
			label="Surveiller ce dataset"
			variant="primary"
			onclick={watch.openModal}
			disabled={!polar_product_id && !polar_checkout_url}
		/>
		{#if watch.watchState === 'error' && watch.error}
			<p class="error-message" role="alert">{watch.error}</p>
		{/if}
	{:else if watch.watchState === 'pending'}
		<div class="pending-state">
			<span class="spinner" aria-hidden="true"></span>
			<span>Traitement en cours...</span>
		</div>
	{/if}

	<Modal title="Surveiller ce dataset" open={watch.modalOpen} onclose={watch.closeModal}>
		{#snippet children()}
			<div class="modal-content">
				<h3 class="modal-title">Surveillance de dataset</h3>
				<p class="modal-description">
					Recevez une alerte par email à chaque changement détecté sur <strong>{dataset_title}</strong>.
					Vous pouvez surveiller jusqu'à 10 datasets.
				</p>
				<p class="modal-price">5 CHF/mois</p>

				<div class="form-group">
					<Input
						id="email-input"
						label="Votre adresse email"
						type="email"
						placeholder="vous@exemple.ch"
						bind:value={watch.email}
						disabled={watch.watchState === 'pending'}
					/>
				</div>

				{#if watch.error}
					<p class="error-message" role="alert">{watch.error}</p>
				{/if}

				<div class="form-actions">
					<Button
						label={watch.watchState === 'pending' ? 'Redirection vers Polar...' : 'Procéder au paiement'}
						variant="primary"
						disabled={watch.watchState === 'pending' || !watch.email || (!polar_product_id && !polar_checkout_url)}
						onclick={watch.handlePolarCheckout}
					/>
					<button class="cancel-btn" onclick={watch.closeModal} disabled={watch.watchState === 'pending'}>
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