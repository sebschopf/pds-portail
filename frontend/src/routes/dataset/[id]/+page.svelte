<script lang="ts">
	import { Breadcrumb, Card, EmptyState, PageLayout, QualityBlock, ResourceList, StructureBlock, WatchDataset } from '$lib';
	import { appendSearchContext, buildSearchHref } from '$lib/navigation/search-context';

	let { data } = $props();

	const dataset = $derived(data.dataset);
	const searchContext = $derived(data.searchContext ?? null);
	const searchHref = $derived(buildSearchHref(searchContext));
	const structure = $derived(dataset?.dataset_structure);
	const orgFilterLink = $derived(
		dataset?.org_id ? `/?org=${encodeURIComponent(dataset.org_id)}&page=1` : null
	);
	const datasetDirectLink = $derived(
		dataset?.id
			? appendSearchContext(`/dataset/${encodeURIComponent(dataset.id)}`, searchContext)
			: null
	);
	const pondérationLink = $derived(
		dataset?.id
			? appendSearchContext(`/dataset/${encodeURIComponent(dataset.id)}/ponderation`, searchContext)
			: null
	);
	const datasetApiLink = $derived(dataset?.id ? `/api/v1/dataset/${encodeURIComponent(dataset.id)}` : null);
	const breadcrumbItems = $derived([
		{ label: 'Recherche', href: searchHref },
		{ label: dataset?.title ?? 'Fiche dataset' }
	]);
	const pageTitle = $derived(dataset?.title ? `${dataset.title} - PDS Portail` : 'Fiche dataset - PDS Portail');
</script>

<svelte:head>
	<title>{pageTitle}</title>
</svelte:head>

<PageLayout>
	<Breadcrumb items={breadcrumbItems} ariaLabel="Fil de navigation dataset" />
	<Card title="Fiche dataset">
		{#if data.status === 'error'}
			<EmptyState
				variant="error"
				title="Impossible de charger ce jeu de données"
				description="Vérifiez votre connexion et réessayez. {data.errorMessage ?? 'Erreur inconnue'}"
			>
				{#snippet action()}
					<a href={searchHref}>Retour à la recherche</a>
				{/snippet}
			</EmptyState>
		{:else if data.status === 'not-found'}
			<EmptyState
				title="Dataset introuvable"
				description="Le jeu de données {data.datasetId} n'existe pas dans notre base. Vérifiez l'URL ou retournez a la recherche."
			>
				{#snippet action()}
					<a href={searchHref}>Retour à la recherche</a>
				{/snippet}
			</EmptyState>
		{:else if data.status === 'contract-error'}
			<EmptyState
				variant="error"
				title="Affichage impossible"
				description="Ce jeu de données n'a pas pu être affiché correctement. Reessayez ou retournez a la recherche."
			>
				{#snippet action()}
					<a href={searchHref}>Retour à la recherche</a>
				{/snippet}
			</EmptyState>
		{:else if dataset}
			<h3 class="title">{dataset.title}</h3>

			{#if data.polar_product_id || data.polar_checkout_url}
				<WatchDataset
					dataset_id={dataset.id}
					dataset_title={dataset.title}
					polar_product_id={data.polar_product_id}
					polar_checkout_url={data.polar_checkout_url}
				/>
			{/if}

			<section class="access-modes" aria-label="Modes d'accès du dataset">
				<h4 class="access-title">Modes d'accès</h4>
				<dl class="access-list">
					<div>
						<dt>Explication du score qualité</dt>
						<dd>
							{#if pondérationLink}
								<a href={pondérationLink}>Comprendre la pondération du score qualité</a>
							{:else}
								Non disponible
							{/if}
						</dd>
					</div>
					<div>
						<dt>Accès direct (URL)</dt>
						<dd>
							{#if datasetDirectLink}
								<a href={datasetDirectLink}>Ouvrir directement cette fiche dataset</a>
							{:else}
								Non disponible
							{/if}
						</dd>
					</div>
					<div>
						<dt>Exploration guidée</dt>
						<dd>
							Naviguer via la recherche puis les ressources associées.
						</dd>
					</div>
					<div>
						<dt>Accès API (développement)</dt>
						<dd>
							{#if datasetApiLink}
								<a href={datasetApiLink}>Consulter le endpoint dataset interne</a>
							{:else}
								Non disponible
							{/if}
						</dd>
					</div>
				</dl>
			</section>

			<dl class="details" aria-label="Informations principales dataset">
				<div>
					<dt>Organisation</dt>
					<dd>{dataset.org_name ?? 'Non renseignée'}</dd>
				</div>
				<div>
					<dt>Description</dt>
					<dd>{dataset.description ?? 'Non renseignée'}</dd>
				</div>
				<div>
					<dt>Licence</dt>
					<dd>{dataset.license ?? 'Non renseignée'}</dd>
				</div>
			</dl>

			{#if dataset.quality_score !== undefined || dataset.completeness !== undefined || dataset.freshness_days !== undefined}
				<QualityBlock
					quality_score={dataset.quality_score}
					completeness={dataset.completeness}
					freshness_days={dataset.freshness_days}
				/>
			{/if}

			{#if structure}
				<StructureBlock structure={structure} />
			{/if}

			<ResourceList resources={dataset.resources} {searchContext} />

			<nav class="links" aria-label="Navigation dataset">
				<a href={searchHref}>Retour à la recherche</a>
				{#if orgFilterLink}
					<a href={orgFilterLink}>Voir les datasets de cette organisation</a>
				{/if}
			</nav>
		{/if}
	</Card>
</PageLayout>

<style>
	h3.title {
		margin: 0 0 var(--space-5);
		line-height: var(--line-height-title);
		font-size: clamp(1.2rem, 1.2vw + 1rem, 1.7rem);
	}

	.access-modes {
		margin-top: var(--space-5);
		padding: var(--space-3);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		background: var(--color-surface);
	}

	.access-title {
		margin: 0 0 var(--space-2);
		font-size: var(--font-size-heading-sm);
		line-height: var(--line-height-title);
	}

	.access-list {
		display: grid;
		gap: var(--space-2);
		margin: 0;
	}

	.access-list div {
		display: grid;
		gap: var(--space-1);
	}

	.access-list dt {
		font-size: var(--font-size-ui);
		font-weight: 700;
		color: var(--color-on-surface-subtle);
	}

	.access-list dd {
		margin: 0;
		font-size: var(--font-size-ui);
		color: var(--color-on-surface-soft);
		overflow-wrap: anywhere;
	}

	.access-list a {
		font-weight: 650;
		text-decoration-thickness: 2px;
	}

	.details {
		display: grid;
		gap: var(--space-4);
		margin: var(--space-5) 0 0;
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
		margin-top: var(--space-5);
	}

	.links a {
		font-weight: 650;
		text-decoration-thickness: 2px;
		overflow-wrap: anywhere;
	}

	@media (max-width: 43.75rem) {
		.links {
			display: grid;
			gap: var(--space-3);
		}
	}

</style>