<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, PageLayout, Card, EmptyState } from '$lib';
	import type { PageData } from './$types';
	import type { ChangeLog } from '$lib/types/watchers';

	let { data } = $props();

	let isAuthenticated = $derived(data.status === 'success');
	let watcherStatus = $derived(data.watchers?.status ?? null);
	let unsubscribeError = $state<string | null>(null);
	let magicLinkEmail = $state('');
	let magicLinkLoading = $state(false);
	let magicLinkMessage = $state<string | null>(null);

	const pageTitle = $derived(isAuthenticated ? 'Mes alertes - PDS Portail' : 'Alertes datasets - PDS Portail');

	function storeWatcherTokens(token: string, datasetIds: string[]) {
		localStorage.setItem('pds-watcher-token', token);

		for (const datasetId of datasetIds) {
			localStorage.setItem(`pds-watcher-${datasetId}`, token);
		}
	}

	function findStoredWatcherToken(): string | null {
		const directToken = localStorage.getItem('pds-watcher-token');
		if (directToken) {
			return directToken;
		}

		for (let index = 0; index < localStorage.length; index += 1) {
			const key = localStorage.key(index);
			if (!key || !key.startsWith('pds-watcher-')) {
				continue;
			}

			const token = localStorage.getItem(key);
			if (token) {
				return token;
			}
		}

		return null;
	}

	onMount(() => {
		if (data.status === 'success' && data.token && data.watchers?.items) {
			storeWatcherTokens(
				data.token,
				data.watchers.items.map((item) => item.dataset_id)
			);
			return;
		}

		if (data.status !== 'not-authenticated') {
			return;
		}

		const storedToken = findStoredWatcherToken();
		if (storedToken) {
			window.location.href = `/alertes?token=${encodeURIComponent(storedToken)}`;
		}
	});

	async function handleRequestMagicLink(event: Event) {
		event.preventDefault();
		magicLinkLoading = true;
		magicLinkMessage = null;
		try {
			const res = await fetch('/api/v1/magic-link', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email: magicLinkEmail })
			});

			if (res.ok) {
				magicLinkMessage = `Un lien d'accès a été envoyé à ${magicLinkEmail}. Vérifiez votre boîte email (validité 15 minutes).`;
				magicLinkEmail = '';
			} else {
				magicLinkMessage = 'Une erreur est survenue. Veuillez réessayer.';
			}
		} catch (err) {
			console.error('Magic link request error:', err);
			magicLinkMessage = 'Erreur de connexion. Veuillez réessayer.';
		} finally {
			magicLinkLoading = false;
		}
	}

	/**
	 * Get grouped changes by dataset
	 */
	function getChangesByDataset(): Record<string, ChangeLog[]> {
		if (!data.alerts?.items) return {};

		return data.alerts.items.reduce(
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
		const alerted = data.alerts?.items.find((item) => item.dataset_id === datasetId);
		if (alerted?.dataset_title) {
			return alerted.dataset_title;
		}
		const watched = data.watchers?.items.find((w) => w.dataset_id === datasetId);
		return watched?.dataset_title || datasetId;
	}

	/**
	 * Handle remove single watched dataset
	 */
	async function handleRemoveWatch(watchedDatasetId: string, datasetTitle: string) {
		if (!confirm(`Êtes-vous sûr d'arrêter la surveillance de "${datasetTitle}" ?`)) {
			return;
		}

		try {
			const res = await fetch(`/api/v1/watchers/${watchedDatasetId}?token=${encodeURIComponent(data.token || '')}`, {
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
						Deux façons d'accéder à vos alertes :
					</p>

					<div class="auth-methods">
						<div class="auth-method">
							<h3>1. Par navigateur reconnu</h3>
							<p>Si un token d'accès est enregistré localement, PDS-Portail tentera de vous reconnecter automatiquement.</p>
						</div>

						<div class="auth-method">
							<h3>2. Par lien email</h3>
							<p>Demandez un lien d'accès temporaire valable 15 minutes. Vous le recevrez par email.</p>
							<form onsubmit={handleRequestMagicLink} class="magic-link-form">
								<input
									type="email"
									placeholder="Votre adresse email"
									aria-label="Votre adresse email"
									bind:value={magicLinkEmail}
									required
									disabled={magicLinkLoading}
								/>
								<button type="submit" disabled={magicLinkLoading || !magicLinkEmail}>
									{magicLinkLoading ? 'Envoi...' : 'Demander un lien'}
								</button>
							</form>
							{#if magicLinkMessage}
								<p class={magicLinkMessage.includes('erreur') ? 'error-message' : 'success-message'}>
									{magicLinkMessage}
								</p>
							{/if}
						</div>
					</div>

					{#if data.errorMessage}
						<p class="error-message" role="alert">{data.errorMessage}</p>
					{/if}
				</div>
			</Card>
		{:else if data.status === 'success'}
			<!-- Authenticated: Show alerts and watched datasets -->
			<Card title="Vos datasets surveillés">
				{#if !data.watchers?.items || data.watchers.items.length === 0}
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
						{#each data.watchers.items as watched (watched.id)}
							<article class="dataset-card">
								<div class="card-header">
									<div class="card-title-section">
										<h3 class="dataset-title">{getDatasetTitle(watched.dataset_id)}</h3>
										<p class="dataset-id">ID: {watched.dataset_id}</p>
									</div>
									<button
										class="remove-btn"
										onclick={() => handleRemoveWatch(watched.id, getDatasetTitle(watched.dataset_id))}
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

			<!-- Subscription information -->
			<Card title="Paramètres d'abonnement">
				<div class="settings-section">
					<p class="settings-text">Vous êtes inscrit avec l'adresse <strong>{data.watchers?.email}</strong>.</p>
					{#if watcherStatus === 'suspended'}
						<p class="warning-message" role="status">
							Votre abonnement est actuellement suspendu. Les alertes restent en pause tant que Polar n'a pas réactivé le watcher.
						</p>
					{/if}
					<p class="settings-text">
						Le token d'accès actuel permet de consulter vos alertes et de gérer vos surveillances existantes.
					</p>
					{#if unsubscribeError}
						<p class="error-message" role="alert">{unsubscribeError}</p>
					{/if}
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
		padding: var(--space-3) 0;
	}

	.auth-intro {
		margin-bottom: var(--space-3);
		font-size: clamp(0.875rem, 1rem, 1.125rem);
		color: var(--color-on-surface-variant);
	}

	.auth-methods {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		margin-bottom: var(--space-4);
	}

	.auth-method {
		padding: var(--space-4);
		background: var(--color-surface-variant);
		border-radius: var(--radius-none);
	}

	.auth-method h3 {
		margin: 0 0 var(--space-2) 0;
		font-size: clamp(1rem, 1.1rem, 1.25rem);
		font-weight: 600;
	}

	.auth-method p {
		margin: 0 0 var(--space-3) 0;
		font-size: clamp(0.875rem, 0.95rem, 1.05rem);
		color: var(--color-on-surface-variant);
	}

	.magic-link-form {
		display: flex;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.magic-link-form input {
		flex: 1;
		min-width: clamp(12rem, 50%, 25rem);
		padding: var(--space-2) var(--space-3);
		border: var(--border-thin) solid var(--color-outline);
		border-radius: var(--radius-none);
		font-size: clamp(0.875rem, 1rem, 1.125rem);
	}

	.magic-link-form button {
		padding: var(--space-2) var(--space-4);
		background: var(--color-primary);
		color: white;
		border: none;
		border-radius: var(--radius-none);
		font-weight: 600;
		cursor: pointer;
		transition: background var(--duration-fast) var(--easing-standard);
	}

	.magic-link-form button:hover:not(:disabled) {
		background: var(--color-primary-container);
	}

	.magic-link-form button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.error-message {
		color: var(--color-error);
		font-size: clamp(0.875rem, 0.95rem, 1.05rem);
		margin: var(--space-3) 0 0 0;
	}

	.success-message {
		color: var(--color-success);
		font-size: clamp(0.875rem, 0.95rem, 1.05rem);
		margin: var(--space-3) 0 0 0;
	}

	.warning-message {
		color: var(--color-warning);
		font-size: clamp(0.875rem, 0.95rem, 1.05rem);
		margin-bottom: var(--space-3);
	}

	.datasets-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.dataset-card {
		padding: var(--space-4);
		border: var(--border-thin) solid var(--color-outline);
		border-radius: var(--radius-none);
		background: var(--color-surface);
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-3);
		margin-bottom: var(--space-3);
	}

	.card-title-section {
		flex: 1;
	}

	.dataset-title {
		margin: 0 0 var(--space-1) 0;
		font-size: clamp(1.05rem, 1.15rem, 1.3rem);
		font-weight: 600;
	}

	.dataset-id {
		margin: 0;
		font-size: clamp(0.75rem, 0.85rem, 0.95rem);
		color: var(--color-on-surface-variant);
	}

	.remove-btn {
		padding: var(--space-2) var(--space-3);
		background: var(--color-surface-variant);
		border: var(--border-thin) solid var(--color-outline);
		border-radius: var(--radius-none);
		cursor: pointer;
		font-size: clamp(0.85rem, 0.9rem, 1rem);
		transition: background var(--duration-fast) var(--easing-standard);
	}

	.remove-btn:hover {
		background: var(--color-error-container);
	}

	.card-metadata {
		margin-bottom: var(--space-3);
	}

	.card-metadata p {
		margin: 0;
		font-size: clamp(0.875rem, 0.95rem, 1.05rem);
		color: var(--color-on-surface-variant);
	}

	.changes-section {
		margin-top: var(--space-4);
	}

	.changes-section h4 {
		margin: 0 0 var(--space-3) 0;
		font-size: clamp(0.95rem, 1rem, 1.1rem);
		font-weight: 600;
	}

	.changes-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.change-item {
		padding: var(--space-3);
		background: var(--color-surface-variant);
		border-radius: var(--radius-none);
	}

	.change-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--space-2);
	}

	.change-header strong {
		font-weight: 600;
	}

	.change-date {
		font-size: clamp(0.75rem, 0.85rem, 0.95rem);
		color: var(--color-on-surface-variant);
	}

	.change-details {
		margin: var(--space-2) 0 0 0;
		font-size: clamp(0.85rem, 0.9rem, 1rem);
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.old-value,
	.new-value {
		font-family: monospace;
		word-break: break-all;
	}

	.notified-info {
		margin: var(--space-2) 0 0 0;
		font-size: clamp(0.75rem, 0.85rem, 0.95rem);
		color: var(--color-on-surface-variant);
		font-style: italic;
	}

	.no-changes {
		margin: 0;
		font-size: clamp(0.875rem, 0.95rem, 1.05rem);
		color: var(--color-on-surface-variant);
	}

	.settings-section {
		padding: var(--space-3) 0;
	}

	.settings-text {
		margin: var(--space-2) 0;
		font-size: clamp(0.875rem, 0.95rem, 1.05rem);
		color: var(--color-on-surface);
	}
</style>
