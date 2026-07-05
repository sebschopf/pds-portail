<script lang="ts">
	import { Button, PageLayout, Card, EmptyState } from '$lib';
	import type { PageData } from './$types';
	import type { WatchedDataset, ChangeLog } from '$lib/types/watchers';

	let { data } = $props();

	let authEmail = $state('');
	let authLoading = $state(false);
	let authError = $state<string | null>(null);
	let isAuthenticated = $derived(data.status === 'success');
	let unsubscribeLoading = $state(false);
	let unsubscribeError = $state<string | null>(null);

	const pageTitle = $derived(isAuthenticated ? 'Mes alertes - PDS Portail' : 'Alertes datasets - PDS Portail');

	/**
	 * Get grouped changes by dataset
	 */
	function getChangesByDataset(): Record<string, ChangeLog[]> {
		if (!data.alerts?.changes) return {};

		return data.alerts.changes.reduce(
			(acc, change) => {
				if (!acc[change.dataset_id]) {
					acc[change.dataset_id] = [];
				}
				acc[change.dataset_id].push(change);
				return acc;
			},
			{} as Record<string, ChangeLog[]>
		);
	}

	/**
	 * Get dataset title from alerts or watched_datasets
	 */
	function getDatasetTitle(datasetId: string): string {
		if (data.alerts?.dataset_details?.[datasetId]?.title) {
			return data.alerts.dataset_details[datasetId].title;
		}
		const watched = data.watchers?.watched_datasets.find((w) => w.dataset_id === datasetId);
		return watched?.dataset_title || datasetId;
	}

	/**
	 * Handle email submission for authentication
	 */
	async function handleEmailAuth() {
		if (!authEmail || !authEmail.includes('@')) {
			authError = 'Veuillez entrer une adresse email valide.';
			return;
		}

		authLoading = true;
		authError = null;

		try {
			const res = await fetch('/api/v1/watchers/auth-link', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email: authEmail })
			});

			if (!res.ok) {
				if (res.status === 404) {
					authError = 'Aucun abonnement trouvé pour cette adresse email.';
				} else {
					authError = 'Impossible d\'envoyer le lien de connexion.';
				}
				return;
			}

			// Success - show success message
			authError = `Un lien de connexion a été envoyé à ${authEmail}. Vérifiez votre boîte mail.`;
			authEmail = '';
		} catch (err) {
			console.error('Auth error:', err);
			authError = 'Erreur de connexion.';
		} finally {
			authLoading = false;
		}
	}

	/**
	 * Handle unsubscribe from all alerts
	 */
	async function handleUnsubscribeAll() {
		if (
			!confirm(
				'Êtes-vous sûr de vouloir vous désabonner de tous les alertes ? Vous arrêterez la surveillance de tous vos datasets.'
			)
		) {
			return;
		}

		unsubscribeLoading = true;
		unsubscribeError = null;

		try {
			const res = await fetch(`/api/v1/watchers?token=${encodeURIComponent(data.token || '')}`, {
				method: 'DELETE'
			});

			if (!res.ok) {
				unsubscribeError = 'Impossible de se désabonner.';
				return;
			}

			// Clear token and redirect
			localStorage.removeItem('pds-watcher-token');
			window.location.href = '/?alert=unsubscribed';
		} catch (err) {
			console.error('Unsubscribe error:', err);
			unsubscribeError = 'Erreur de connexion.';
		} finally {
			unsubscribeLoading = false;
		}
	}

	/**
	 * Handle remove single watched dataset
	 */
	async function handleRemoveWatch(datasetId: string, datasetTitle: string) {
		if (!confirm(`Êtes-vous sûr d'arrêter la surveillance de "${datasetTitle}" ?`)) {
			return;
		}

		try {
			const res = await fetch(`/api/v1/watchers/${datasetId}?token=${encodeURIComponent(data.token || '')}`, {
				method: 'DELETE'
			});

			if (res.ok) {
				// Reload page
				window.location.reload();
			} else {
				unsubscribeError = 'Impossible d\'arrêter la surveillance.';
			}
		} catch (err) {
			console.error('Remove watch error:', err);
			unsubscribeError = 'Erreur de connexion.';
		}
	}

	function formatDate(isoDate: string): string {
		return new Intl.DateTimeFormat('fr-CH', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		}).format(new Date(isoDate));
	}

	function getChangeTypeLabel(changeType: string): string {
		const labels: Record<string, string> = {
			metadata_updated: 'Métadonnées mises à jour',
			resource_added: 'Nouvelle ressource',
			resource_removed: 'Ressource supprimée',
			quality_degraded: 'Qualité dégradée',
			link_broken: 'Lien cassé'
		};
		return labels[changeType] || changeType;
	}
</script>

<svelte:head>
	<title>{pageTitle}</title>
</svelte:head>

<PageLayout>
	<div class="alerts-container">
		<h1>Mes alertes datasets</h1>

		{#if data.status === 'error'}
			<Card title="Erreur de chargement">
				<EmptyState
					variant="error"
					title="Erreur de chargement"
					description={data.errorMessage || 'Impossible de charger vos alertes.'}
				>
					{#snippet action()}
						<a href="/">Retour à l'accueil</a>
					{/snippet}
				</EmptyState>
			</Card>
		{:else if data.status === 'not-authenticated' || !isAuthenticated}
			<Card title="Accéder à vos alertes">
				<div class="auth-form">
					<p class="auth-intro">
						Entrez votre adresse email pour recevoir un lien de connexion sécurisé.
					</p>

					<div class="form-group">
						<label for="auth-email" class="form-label">Adresse email</label>
						<input
							id="auth-email"
							type="email"
							placeholder="vous@exemple.ch"
							bind:value={authEmail}
							disabled={authLoading}
							class="form-input"
						/>
					</div>

					{#if authError}
						<p class={authError.includes('envoyé') ? 'success-message' : 'error-message'} role="alert">
							{authError}
						</p>
					{/if}

					<Button
						label={authLoading ? 'Envoi en cours...' : 'Envoyer le lien'}
						variant="primary"
						disabled={authLoading || !authEmail}
						onclick={handleEmailAuth}
					/>
				</div>
			</Card>
		{:else if data.status === 'success'}
			<!-- Authenticated: Show alerts and watched datasets -->
			<Card title="Vos datasets surveillés">
				{#if !data.watchers?.watched_datasets || data.watchers.watched_datasets.length === 0}
					<EmptyState
						title="Aucun dataset surveillé"
						description="Vous ne surveillez actuellement aucun dataset. Retournez sur les fiches dataset pour en ajouter à la surveillance."
					>
						{#snippet action()}
							<a href="/">Retour à la recherche</a>
						{/snippet}
					</EmptyState>
				{:else}
					<div class="datasets-list">
						{#each data.watchers.watched_datasets as watched (watched.id)}
							<article class="dataset-card">
								<div class="card-header">
									<div class="card-title-section">
										<h3 class="dataset-title">{getDatasetTitle(watched.dataset_id)}</h3>
										<p class="dataset-id">ID: {watched.dataset_id}</p>
									</div>
									<button
										class="remove-btn"
										onclick={() => handleRemoveWatch(watched.dataset_id, getDatasetTitle(watched.dataset_id))}
										aria-label="Arrêter la surveillance de {getDatasetTitle(watched.dataset_id)}"
									>
										Arrêter la surveillance
									</button>
								</div>

								<div class="card-metadata">
									<p>
										<strong>Commencée le :</strong>
										{formatDate(watched.created_at)}
									</p>
									{#if watched.last_known_quality_score !== null}
										<p>
											<strong>Score qualité :</strong>
											{watched.last_known_quality_score}/100
										</p>
									{/if}
									{#if watched.last_known_resource_count !== null}
										<p>
											<strong>Ressources :</strong>
											{watched.last_known_resource_count}
										</p>
									{/if}
								</div>

								<!-- Changes history for this dataset -->
								{#if (getChangesByDataset()[watched.dataset_id] || []).length > 0}
									<div class="changes-section">
										<h4>Historique des changements</h4>
										<ul class="changes-list">
											{#each (getChangesByDataset()[watched.dataset_id] || []) as change (change.id)}
												<li class="change-item">
													<div class="change-header">
														<strong>{getChangeTypeLabel(change.change_type)}</strong>
														<time class="change-date">{formatDate(change.detected_at)}</time>
													</div>
													{#if change.previous_value && change.new_value}
														<p class="change-details">
															<span class="old-value">Avant: {change.previous_value}</span>
															<span class="new-value">Après: {change.new_value}</span>
														</p>
													{:else if change.new_value}
														<p class="change-details">{change.new_value}</p>
													{/if}
													{#if change.notified_at}
														<p class="notified-info">
															Notification envoyée: {formatDate(change.notified_at)}
														</p>
													{/if}
												</li>
											{/each}
										</ul>
									</div>
								{:else}
									<p class="no-changes">Aucun changement détecté pour le moment.</p>
								{/if}
							</article>
						{/each}
					</div>
				{/if}
			</Card>

			<!-- Unsubscribe section -->
			<Card title="Paramètres d'abonnement">
				<div class="settings-section">
					<p class="settings-text">
						Vous êtes inscrit avec l'adresse <strong>{data.watchers?.watcher.email}</strong>.
					</p>
					{#if unsubscribeError}
						<p class="error-message" role="alert">{unsubscribeError}</p>
					{/if}
					<button
						class="unsubscribe-btn"
						onclick={handleUnsubscribeAll}
						disabled={unsubscribeLoading}
					>
						{unsubscribeLoading ? 'Désabonnement en cours...' : 'Se désabonner de tous les alertes'}
					</button>
				</div>
			</Card>
		{/if}
	</div>
</PageLayout>

<style>
	.alerts-container {
		max-width: 900px;
		margin: 0 auto;
	}

	h1 {
		font-size: clamp(1.5rem, 2rem, 2.5rem);
		font-weight: 700;
		margin-bottom: var(--space-5);
		color: var(--color-on-surface);
	}

	.auth-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.auth-intro {
		margin: 0;
		color: var(--color-on-surface-secondary);
		line-height: var(--line-height-relaxed);
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.form-label {
		font-weight: 500;
		font-size: clamp(0.75rem, 0.9rem, 1rem);
	}

	.form-input {
		border: var(--border-thin) solid var(--color-border);
		background: var(--color-surface);
		border-radius: var(--radius-none);
		padding: var(--space-3) var(--space-4);
		min-height: var(--size-control-md);
		color: var(--color-on-surface);
		font-size: var(--font-size-ui);
	}

	.form-input:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	.form-input:disabled {
		opacity: 0.6;
		cursor: not-allowed;
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

	.success-message {
		padding: var(--space-2) var(--space-3);
		background: var(--color-success-subtle);
		border-left: 3px solid var(--color-success);
		color: var(--color-on-surface);
		font-size: clamp(0.75rem, 0.9rem, 1rem);
		margin: 0;
		border-radius: var(--radius-none);
	}

	.datasets-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.dataset-card {
		border: 1px solid var(--color-border);
		border-radius: var(--radius-none);
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		background: var(--color-surface);
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-3);
	}

	.card-title-section {
		flex: 1;
	}

	.dataset-title {
		margin: 0 0 var(--space-1) 0;
		font-size: var(--font-size-heading-md);
		font-weight: 700;
	}

	.dataset-id {
		margin: 0;
		font-size: clamp(0.75rem, 0.85rem, 1rem);
		color: var(--color-on-surface-muted);
	}

	.remove-btn {
		padding: var(--space-2) var(--space-3);
		background: transparent;
		border: 1px solid var(--color-error);
		border-radius: var(--radius-none);
		color: var(--color-error);
		font-weight: 500;
		cursor: pointer;
		transition: background-color 140ms ease;
		white-space: nowrap;
	}

	.remove-btn:hover {
		background: var(--color-error-subtle);
	}

	.remove-btn:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	.card-metadata {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: var(--space-2);
		font-size: clamp(0.75rem, 0.9rem, 1rem);
	}

	.card-metadata p {
		margin: 0;
	}

	.changes-section {
		border-top: 1px solid var(--color-border);
		padding-top: var(--space-3);
	}

	.changes-section h4 {
		margin: 0 0 var(--space-2) 0;
		font-size: var(--font-size-ui);
		font-weight: 600;
	}

	.changes-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.change-item {
		padding: var(--space-2) var(--space-3);
		background: var(--color-surface-muted);
		border-radius: var(--radius-none);
		border-left: 3px solid var(--color-primary);
	}

	.change-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--space-2);
		margin-bottom: var(--space-1);
	}

	.change-header strong {
		color: var(--color-on-surface);
	}

	.change-date {
		font-size: clamp(0.75rem, 0.85rem, 1rem);
		color: var(--color-on-surface-muted);
	}

	.change-details {
		margin: var(--space-1) 0 0 0;
		font-size: clamp(0.75rem, 0.9rem, 1rem);
		color: var(--color-on-surface-secondary);
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.old-value,
	.new-value {
		display: block;
		padding: var(--space-1) var(--space-2);
		background: var(--color-surface);
		border-radius: var(--radius-none);
		font-family: monospace;
	}

	.notified-info {
		margin: var(--space-1) 0 0 0;
		font-size: clamp(0.75rem, 0.85rem, 1rem);
		color: var(--color-on-surface-muted);
		font-style: italic;
	}

	.no-changes {
		margin: var(--space-2) 0 0 0;
		color: var(--color-on-surface-muted);
		font-size: clamp(0.75rem, 0.9rem, 1rem);
	}

	.settings-section {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.settings-text {
		margin: 0;
		color: var(--color-on-surface-secondary);
	}

	.unsubscribe-btn {
		padding: var(--space-3) var(--space-4);
		background: var(--color-error-subtle);
		border: 1px solid var(--color-error);
		border-radius: var(--radius-none);
		color: var(--color-error);
		font-weight: 600;
		cursor: pointer;
		transition: background-color 140ms ease, color 140ms ease;
	}

	.unsubscribe-btn:hover:not(:disabled) {
		background: var(--color-error);
		color: white;
	}

	.unsubscribe-btn:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	.unsubscribe-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	/* Mobile adaptation */
	@media (max-width: 40rem) {
		h1 {
			font-size: var(--font-size-display-metric);
		}

		.card-header {
			flex-direction: column;
			align-items: flex-start;
		}

		.remove-btn {
			align-self: flex-start;
		}

		.card-metadata {
			grid-template-columns: 1fr;
		}

		.change-header {
			flex-direction: column;
			align-items: flex-start;
		}
	}
</style>
