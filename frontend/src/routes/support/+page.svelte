<script lang="ts">
	import { Button, Card, EmptyState, PageLayout } from '$lib';

	type SupportPageData = {
		status: 'idle' | 'loaded' | 'not-found' | 'error' | 'not-configured';
		email: string;
		notice: string | null;
		errorMessage: string | null;
		diagnostics: {
			watcher: {
				watcher_id: string;
				watcher_status: string;
				subscription_id_present: boolean;
				watched_datasets_count: number;
				last_webhook_at: string | null;
				last_magic_link_at: string | null;
			};
			subscription: {
				watcher_id: string;
				subscription_state: string;
				subscription_id_masked: string | null;
				updated_at: string;
			};
			webhooks: Array<{
				event_type: string;
				received_at: string;
				delivery_status: string;
				correlation_id: string | null;
			}>;
			magicLinks: {
				watcher_id: string;
				last_issued_at: string | null;
				last_used_at: string | null;
				active_unexpired_count: number;
				expired_unconsumed_count: number;
			};
			deliverability: {
				watcher_id: string;
				last_send_status: string | null;
				last_send_at: string | null;
				provider_message_id_masked: string | null;
				recent_error_code: string | null;
				recent_error_count_24h: number;
			};
		} | null;
	};

	let { data }: { data: SupportPageData } = $props();

	const noticeLabels: Record<string, string> = {
		resent: 'Magic link renvoyé avec succès.',
		queued: 'Magic link mis en file d attente: verifier la configuration SMTP.',
		suspended: 'Le watcher est suspendu: aucun renvoi effectué.',
		'rate-limited': 'Renvoi temporairement limité pour éviter les doublons.',
		'not-configured': 'Le module support n\'est pas configuré sur le serveur.',
		'missing-data': 'Le formulaire de support est incomplet.',
		error: 'Le renvoi a échoué.'
	};

	function formatLabel(value: string | null | undefined): string {
		return value && value.trim().length > 0 ? value : 'Non renseigné';
	}
</script>

<svelte:head>
	<title>Support interne - PDS Portail</title>
</svelte:head>

<PageLayout as="main">
	<section class="hero">
		<p class="eyebrow">Support interne protégé</p>
		<h2>Diagnostic incidents paiement mais pas d’accès</h2>
		<p>
			Cette page interroge le backend support avec un jeton serveur uniquement.
			Aucun secret administratif n'est transmis au navigateur.
		</p>
	</section>

	<Card title="Lancer un diagnostic">
		<form class="search-form" method="GET">
			<label for="support-email">Adresse email</label>
			<div class="search-row">
				<input id="support-email" name="email" type="email" required value={data.email} />
				<Button label="Diagnostiquer" type="submit" />
			</div>
		</form>
		{#if data.notice}
			<p class="notice" role="status">{noticeLabels[data.notice] ?? data.notice}</p>
		{/if}
	</Card>

	{#if data.status === 'not-configured'}
		<Card title="Configuration absente">
			<EmptyState
				variant="error"
				title="Support interne indisponible"
				description={data.errorMessage ?? 'Le serveur ne fournit pas le token interne requis.'}
			/>
		</Card>
	{:else if data.status === 'idle'}
		<Card title="Procédure support">
			<ol class="steps">
				<li>Identifier le watcher par email.</li>
				<li>Vérifier le statut d’abonnement et `subscription_id`.</li>
				<li>Contrôler les derniers webhooks, magic links et la délivrabilité email.</li>
				<li>Renvoyer un magic link seulement si le diagnostic converge.</li>
			</ol>
		</Card>
	{:else if data.status === 'not-found'}
		<Card title="Aucun watcher trouvé">
			<EmptyState
				variant="error"
				title="Watcher introuvable"
				description={data.errorMessage ?? 'Aucun watcher ne correspond à cette adresse email.'}
			/>
		</Card>
	{:else if data.status === 'error'}
		<Card title="Erreur de diagnostic">
			<EmptyState
				variant="error"
				title="Diagnostic indisponible"
				description={data.errorMessage ?? 'Impossible de charger le diagnostic support.'}
			/>
		</Card>
	{:else if data.diagnostics}
		<div class="diagnostics-grid">
			<Card title="Watcher">
				<dl class="summary-list">
					<div><dt>Email</dt><dd>{data.email}</dd></div>
					<div><dt>Statut</dt><dd>{data.diagnostics.watcher.watcher_status}</dd></div>
					<div><dt>subscription_id</dt><dd>{data.diagnostics.watcher.subscription_id_present ? 'Présent' : 'Absent'}</dd></div>
					<div><dt>Datasets surveillés</dt><dd>{data.diagnostics.watcher.watched_datasets_count}</dd></div>
					<div><dt>Dernier webhook</dt><dd>{formatLabel(data.diagnostics.watcher.last_webhook_at)}</dd></div>
					<div><dt>Dernier magic link</dt><dd>{formatLabel(data.diagnostics.watcher.last_magic_link_at)}</dd></div>
				</dl>
			</Card>

			<Card title="Abonnement">
				<dl class="summary-list">
					<div><dt>État</dt><dd>{data.diagnostics.subscription.subscription_state}</dd></div>
					<div><dt>Identifiant masqué</dt><dd>{formatLabel(data.diagnostics.subscription.subscription_id_masked)}</dd></div>
					<div><dt>Mise à jour</dt><dd>{data.diagnostics.subscription.updated_at}</dd></div>
				</dl>
			</Card>

			<Card title="Magic links">
				<dl class="summary-list">
					<div><dt>Dernier émis</dt><dd>{formatLabel(data.diagnostics.magicLinks.last_issued_at)}</dd></div>
					<div><dt>Dernier utilisé</dt><dd>{formatLabel(data.diagnostics.magicLinks.last_used_at)}</dd></div>
					<div><dt>Actifs</dt><dd>{data.diagnostics.magicLinks.active_unexpired_count}</dd></div>
					<div><dt>Expirés non consommés</dt><dd>{data.diagnostics.magicLinks.expired_unconsumed_count}</dd></div>
				</dl>
			</Card>

			<Card title="Délivrabilité email">
				<dl class="summary-list">
					<div><dt>Dernier envoi</dt><dd>{formatLabel(data.diagnostics.deliverability.last_send_status)}</dd></div>
					<div><dt>Dernier envoi à</dt><dd>{formatLabel(data.diagnostics.deliverability.last_send_at)}</dd></div>
					<div><dt>Message provider masqué</dt><dd>{formatLabel(data.diagnostics.deliverability.provider_message_id_masked)}</dd></div>
					<div><dt>Erreur récente</dt><dd>{formatLabel(data.diagnostics.deliverability.recent_error_code)}</dd></div>
					<div><dt>Erreurs 24h</dt><dd>{data.diagnostics.deliverability.recent_error_count_24h}</dd></div>
				</dl>
			</Card>

			<Card title="Derniers webhooks">
				{#if data.diagnostics.webhooks.length === 0}
					<p>Aucun webhook disponible.</p>
				{:else}
					<ul class="events-list">
						{#each data.diagnostics.webhooks as item}
							<li>
								<strong>{item.event_type}</strong>
								<p>{item.delivery_status} · {item.received_at}</p>
							</li>
						{/each}
					</ul>
				{/if}
			</Card>

			<Card title="Action support">
				{#if data.diagnostics.watcher.watcher_status === 'active'}
					<form method="POST" action="?/resend" class="resend-form">
						<input type="hidden" name="email" value={data.email} />
						<input type="hidden" name="watcher_id" value={data.diagnostics.watcher.watcher_id} />
						<Button label="Renvoyer le magic link" type="submit" />
					</form>
				{:else}
					<p>Le renvoi est bloqué tant que le watcher n’est pas actif.</p>
				{/if}
			</Card>
		</div>
	{/if}
</PageLayout>

<style>
	.hero {
		display: grid;
		gap: var(--space-2);
		padding: var(--space-4);
		border: var(--border-thin) solid var(--color-border);
		background: linear-gradient(135deg, var(--color-surface), var(--color-surface-muted));
	}

	.eyebrow {
		margin: 0;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		font-size: var(--font-size-caption);
		font-weight: 700;
		color: var(--color-primary);
	}

	h2 {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(1.35rem, 2vw + 1rem, 2.2rem);
		line-height: var(--line-height-title);
	}

	.hero p,
	.notice,
	.steps,
	.summary-list dd,
	.events-list p {
		margin: 0;
		color: var(--color-on-surface);
	}

	.search-form {
		display: grid;
		gap: var(--space-2);
	}

	.search-row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: var(--space-3);
	}

	label {
		font-weight: 650;
	}

	input {
		width: 100%;
		min-height: var(--size-control-lg);
		padding: var(--space-3);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		background: var(--color-surface);
		color: var(--color-on-surface);
	}

	input:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	.notice {
		padding-top: var(--space-2);
		color: var(--color-primary);
		font-weight: 650;
	}

	.diagnostics-grid {
		display: grid;
		gap: var(--space-4);
	}

	.summary-list {
		display: grid;
		gap: var(--space-2);
	}

	.summary-list div {
		display: grid;
		gap: var(--space-1);
		padding-bottom: var(--space-2);
		border-bottom: var(--border-thin) solid var(--color-border);
	}

	.summary-list dt {
		font-size: var(--font-size-caption);
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--color-on-surface-subtle);
	}

	.summary-list dd,
	.events-list p {
		font-size: var(--font-size-ui);
	}

	.events-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: var(--space-2);
	}

	.events-list li {
		padding-bottom: var(--space-2);
		border-bottom: var(--border-thin) solid var(--color-border);
	}

	.resend-form {
		display: grid;
		gap: var(--space-2);
	}

	@media (max-width: 43.75rem) {
		.search-row {
			grid-template-columns: 1fr;
		}
	}
</style>