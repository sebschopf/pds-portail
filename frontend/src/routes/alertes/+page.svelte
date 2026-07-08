<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, PageLayout, Card, EmptyState } from '$lib';
	import { useAlerts } from '$lib/runes/alerts.svelte';
	import type { PageData } from './$types';
	import type { ChangeLog } from '$lib/types/watchers';

	let { data } = $props();

	const alerts = useAlerts(() => data);

	onMount(() => {
		alerts.initTokens();
	});

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
	<title>{alerts.pageTitle}</title>
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
		{:else if data.status === 'not-authenticated' || !alerts.isAuthenticated}
			<Card title="Accéder à vos alertes">
				<div class="auth-form">
					<div class="auth-recap" role="note">
						<h3>Rappel du fonctionnement</h3>
						<p>
							Le service de surveillance de datasets est <strong>payant</strong>
							(5 CHF/mois, jusqu'à 10 datasets).
							Après votre paiement sur Polar, vous avez reçu un email de bienvenue contenant
							un lien vers votre tableau de bord. Cliquez sur ce lien pour voir vos datasets
							surveillés et l'historique des changements.
						</p>
						<p>
							Consultez le <a href="/manuel#surveillance">manuel d'utilisation</a> pour le détail du service.
							Un problème ? <a href="/contact">Formulaire de contact</a>
						</p>
					</div>

					<div class="auth-recap auth-recap-help" role="note">
						<h3>Vous avez changé de navigateur ou perdu l'email ?</h3>
						<p>
							Pas d'inquiétude. Entrez simplement l'adresse email que vous avez utilisée
							lors du paiement, et nous vous enverrons un <strong>nouveau lien d'accès</strong>
							(valable 15 minutes). Vous pourrez alors consulter vos alertes depuis ce navigateur.
						</p>
					</div>

					<form onsubmit={alerts.handleRequestMagicLink} class="magic-link-form magic-link-form--centered">
						<input
							type="email"
							placeholder="Votre adresse email"
							aria-label="Votre adresse email"
							bind:value={alerts.magicLinkEmail}
							required
							disabled={alerts.magicLinkLoading}
						/>
						<button type="submit" disabled={alerts.magicLinkLoading || !alerts.magicLinkEmail}>
							{alerts.magicLinkLoading ? 'Envoi...' : 'Recevoir un lien'}
						</button>
					</form>
					{#if alerts.magicLinkMessage}
						<p class={alerts.magicLinkMessage.includes('erreur') ? 'error-message' : 'success-message'}>
							{alerts.magicLinkMessage}
						</p>
					{/if}

					<div class="auth-divider" aria-hidden="true"></div>

					<p class="auth-intro">
						Déjà connecté sur ce navigateur ?
					</p>

					<div class="auth-methods">
						<div class="auth-method">
							<h3>Par navigateur reconnu</h3>
							<p>Si vous avez déjà ouvert le tableau de bord sur ce navigateur, PDS-Portail vous reconnecte automatiquement.</p>
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
							{@const dsTitle = getDatasetTitle(watched.dataset_id)}
							{@const datasetChanges = (getChangesByDataset()[watched.dataset_id] || [])}
							<article class="dataset-card">
								<div class="card-header">
									<div class="card-title-section">
										<h3 class="dataset-title">{dsTitle}</h3>
										<p class="dataset-id">ID: {watched.dataset_id}</p>
									</div>
									<button
										class="remove-btn"
										onclick={() => alerts.handleRemoveWatch(watched.id, dsTitle)}
										aria-label="Arrêter la surveillance de {dsTitle}"
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
								{#if datasetChanges.length > 0}
									<div class="changes-section">
										<h4>Historique des changements</h4>
										<ul class="changes-list">
											{#each datasetChanges as change (change.id)}
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
					{#if alerts.watcherStatus === 'suspended'}
						<p class="warning-message" role="status">
							Votre abonnement est actuellement suspendu. Les alertes restent en pause tant que Polar n'a pas réactivé le watcher.
						</p>
					{/if}
					<p class="settings-text">
						Le token d'accès actuel permet de consulter vos alertes et de gérer vos surveillances existantes.
					</p>
					{#if alerts.unsubscribeError}
						<p class="error-message" role="alert">{alerts.unsubscribeError}</p>
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

	.auth-recap {
		padding: var(--space-4);
		margin-bottom: var(--space-5);
		background: var(--color-surface-variant);
		border: var(--border-thin) solid var(--color-outline);
		border-radius: var(--radius-none);
	}

	.auth-recap h3 {
		margin: 0 0 var(--space-2) 0;
		font-size: clamp(1rem, 1.1rem, 1.25rem);
		font-weight: 600;
	}

	.auth-recap p {
		margin: 0 0 var(--space-2) 0;
		font-size: clamp(0.875rem, 0.95rem, 1.05rem);
		color: var(--color-on-surface-variant);
		line-height: var(--line-height-relaxed);
	}

	.auth-recap p:last-child {
		margin-bottom: 0;
	}

	.auth-recap a {
		color: var(--color-primary);
		font-weight: 600;
	}

	.auth-recap-help {
		padding: var(--space-4);
		margin-bottom: var(--space-5);
		background: var(--color-success-subtle);
		border: var(--border-thin) solid var(--color-success);
		border-radius: var(--radius-none);
	}

	.auth-recap-help h3 {
		margin: 0 0 var(--space-2) 0;
		font-size: clamp(1rem, 1.1rem, 1.25rem);
		font-weight: 600;
		color: var(--color-success);
	}

	.auth-recap-help p {
		margin: 0;
		font-size: clamp(0.875rem, 0.95rem, 1.05rem);
		line-height: var(--line-height-relaxed);
	}

	.magic-link-form--centered {
		justify-content: center;
		margin-bottom: var(--space-3);
	}

	.auth-divider {
		border-top: 1px solid var(--color-outline-variant);
		margin: var(--space-4) 0 var(--space-5);
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