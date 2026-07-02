<script lang="ts">
	import { Breadcrumb, Card, EmptyState, ExploreDataset, PageLayout, StateBadge } from '$lib';
	import { appendSearchContext, buildSearchHref } from '$lib/navigation/search-context';
	import { getSafeExternalUrl } from '$lib/security/external-url';

	let { data } = $props();
	const resource = $derived(data.resource);
	const searchContext = $derived(data.searchContext ?? null);
	const searchHref = $derived(buildSearchHref(searchContext));
	const datasetLink = $derived(
		resource?.dataset_id
			? appendSearchContext(`/dataset/${encodeURIComponent(resource.dataset_id)}`, searchContext)
			: null
	);
	const safeSourceUrl = $derived(getSafeExternalUrl(resource?.url));
	const isPreviewCompatible = $derived.by(() => {
		const format = resource?.format?.toLowerCase();
		return format === 'csv' || format === 'json' || format === 'txt';
	});
	const previewState = $derived.by(() =>
		isPreviewCompatible
			? {
				label: 'Prévisualisation accessible via clé API',
				variant: 'success' as const,
				sectionClass: 'compatible'
			}
			: {
				label: 'Format non pris en charge',
				variant: 'warning' as const,
				sectionClass: 'unsupported'
			}
	);
	const previewText = $derived.by(() => {
		if (!resource) {
			return '';
		}

		if ((resource.format ?? '').toLowerCase() === 'csv') {
			return 'Aperçu CSV: en-têtes détectés, quelques lignes de données et séparateur standard attendus.';
		}

		if ((resource.format ?? '').toLowerCase() === 'json') {
			return 'Aperçu JSON: structure objet/tableau attendue avec clés principales et échantillon de valeurs.';
		}

		return 'Aperçu texte: extrait court de contenu brut pour vérification rapide du format.';
	});
	const breadcrumbItems = $derived([
		{ label: 'Recherche', href: searchHref },
		{ label: resource?.dataset_title ?? 'Dataset', href: datasetLink ?? undefined },
		{ label: resource?.name ?? 'Fiche ressource' }
	]);
	const pageTitle = $derived(resource?.name ? `${resource.name} - PDS Portail` : 'Fiche ressource - PDS Portail');
</script>

<svelte:head>
	<title>{pageTitle}</title>
</svelte:head>

<PageLayout>
	<Breadcrumb items={breadcrumbItems} ariaLabel="Fil de navigation ressource" />
	<Card title="Fiche ressource">
		{#if data.status === 'error'}
			<EmptyState
				variant="error"
				title="Erreur lors du chargement de la ressource"
				description={data.errorMessage ?? 'Vérifiez votre connexion et réessayez.'}
			>
				{#snippet action()}
					<a href={searchHref}>Retour à la recherche</a>
				{/snippet}
			</EmptyState>
		{:else if data.status === 'not-found'}
			<EmptyState
				title="Ressource introuvable"
				description="La ressource {data.resourceId} n'existe pas dans notre base. Vérifiez l'URL ou retournez à la recherche."
			>
				{#snippet action()}
					<a href={searchHref}>Retour à la recherche</a>
				{/snippet}
			</EmptyState>
		{:else if data.status === 'contract-error'}
			<EmptyState
				variant="error"
				title="Affichage impossible"
				description="Cette ressource n'a pas pu être affichée correctement. Réessayez ou retournez à la recherche."
			>
				{#snippet action()}
					<a href={searchHref}>Retour à la recherche</a>
				{/snippet}
			</EmptyState>
		{:else if resource}
			<h3 class="title">{resource.name}</h3>

			<dl class="details" aria-label="Informations ressource">
				<div>
					<dt>Format</dt>
					<dd>{resource.format ?? 'Non renseigné'}</dd>
				</div>
				<div>
					<dt>Taille</dt>
					<dd>{resource.size_bytes ?? 'Non renseignée'}</dd>
				</div>
				<div>
					<dt>Création</dt>
					<dd>{resource.created ?? 'Non renseignée'}</dd>
				</div>
				<div>
					<dt>Dernière modification</dt>
					<dd>{resource.last_modified ?? 'Non renseignée'}</dd>
				</div>
				<div>
					<dt>Dataset parent</dt>
					<dd>{resource.dataset_title ?? 'Non renseigné'}</dd>
				</div>
			</dl>

			<section class={`preview ${previewState.sectionClass}`} aria-label="Prévisualisation ressource">
				<div class="preview-header">
					<h4 class="preview-title">Prévisualisation courte</h4>
					<StateBadge label={previewState.label} variant={previewState.variant} />
				</div>
				{#if isPreviewCompatible}
					<p class="preview-text">{previewText}</p>
				{:else}
					<p class="preview-text" role="status">
						Prévisualisation non disponible pour le format {resource.format ?? 'inconnu'}.
					</p>
				{/if}
			</section>

			<ExploreDataset resourceId={resource.id} />

			<nav class="links" aria-label="Navigation ressource">
				<a href={searchHref}>Retour à la recherche</a>
				{#if datasetLink}
					<a href={datasetLink}>Retour à la fiche dataset</a>
				{/if}
				{#if safeSourceUrl}
					<a href={safeSourceUrl} target="_blank" rel="noreferrer noopener">Ouvrir l'URL source</a>
				{:else if resource.url}
					<span class="link-disabled" role="status">URL source non conforme</span>
				{/if}
			</nav>
		{/if}
	</Card>
</PageLayout>

<style>	h3.title {
		margin: 0;
		line-height: var(--line-height-title);
		font-size: clamp(1.2rem, 1.2vw + 1rem, 1.7rem);
	}

	.details {
		display: grid;
		gap: var(--space-4);
		margin: var(--space-4) 0 0;
	}

	.preview {
		margin-top: var(--space-4);
		padding: var(--space-3);
		background: var(--color-surface);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
	}

	.preview.compatible {
		background: color-mix(in oklch, var(--color-success) 10%, var(--color-surface-muted));
		border-color: var(--color-success);
	}

	.preview.unsupported {
		background: color-mix(in oklch, var(--color-warning) 18%, var(--color-surface-muted));
		border-color: var(--color-warning);
	}

	.preview-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-3);
		margin-bottom: var(--space-2);
	}

	.preview-title {
		margin: 0;
		font-size: var(--font-size-heading-sm);
		line-height: var(--line-height-title);
	}

	.preview-text {
		margin: 0;
		font-size: var(--font-size-ui);
		color: var(--color-on-surface-soft);
		overflow-wrap: anywhere;
	}

	.details div {
		display: grid;
		gap: var(--space-1);
		padding: var(--space-3);
		background: var(--color-surface-muted);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
	}

	dt {
		font-weight: 700;
	}

	dd {
		margin: 0;
		overflow-wrap: anywhere;
	}

	.links {
		display: flex;
		gap: var(--space-4);
		flex-wrap: wrap;
		margin-top: var(--space-4);
	}

	.links a {
		font-weight: 650;
		text-decoration-thickness: 2px;
		overflow-wrap: anywhere;
	}

	.link-disabled {
		font-size: var(--font-size-ui);
		color: var(--color-on-surface-subtle);
	}

	@media (max-width: 43.75rem) {
		.links {
			display: grid;
			gap: var(--space-3);
		}
	}
</style>
