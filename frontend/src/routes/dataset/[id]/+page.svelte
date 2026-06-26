<script lang="ts">
	import { Breadcrumb, Card, EmptyState, QualityBlock, ResourceList, StructureBlock } from '$lib';
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
	const ponderationLink = $derived(
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

<section class="stack">
	<Breadcrumb items={breadcrumbItems} ariaLabel="Fil de navigation dataset" />
	<Card title="Fiche dataset" subtitle="Contrat backend endpoint dataset detail">
		{#if data.status === 'error'}
			<EmptyState
				variant="error"
				title="Impossible de charger ce jeu de donnees"
				description="Verifiez votre connexion et reessayez. {data.errorMessage ?? 'Erreur inconnue'}"
			>
				{#snippet action()}
					<a href={searchHref}>Retour a la recherche</a>
				{/snippet}
			</EmptyState>
		{:else if data.status === 'not-found'}
			<EmptyState
				title="Dataset introuvable"
				description="Le jeu de donnees {data.datasetId} n'existe pas dans notre base. Verifiez l'URL ou retournez a la recherche."
			>
				{#snippet action()}
					<a href={searchHref}>Retour a la recherche</a>
				{/snippet}
			</EmptyState>
		{:else if data.status === 'contract-error'}
			<EmptyState
				variant="error"
				title="Affichage impossible"
				description="Ce jeu de donnees n'a pas pu etre affiche correctement. Reessayez ou retournez a la recherche."
			>
				{#snippet action()}
					<a href={searchHref}>Retour a la recherche</a>
				{/snippet}
			</EmptyState>
		{:else if dataset}
			<h3 class="title">{dataset.title}</h3>

			<section class="access-modes" aria-label="Modes d acces du dataset">
				<h4 class="access-title">Modes d acces</h4>
				<dl class="access-list">
					<div>
						<dt>Explication du score qualite</dt>
						<dd>
							{#if ponderationLink}
								<a href={ponderationLink}>Comprendre la ponderation du score qualite</a>
							{:else}
								Non disponible
							{/if}
						</dd>
					</div>
					<div>
						<dt>Acces direct (URL)</dt>
						<dd>
							{#if datasetDirectLink}
								<a href={datasetDirectLink}>Ouvrir directement cette fiche dataset</a>
							{:else}
								Non disponible
							{/if}
						</dd>
					</div>
					<div>
						<dt>Exploration guidee</dt>
						<dd>
							Naviguer via la recherche puis les ressources associees.
						</dd>
					</div>
					<div>
						<dt>Acces API (developpement)</dt>
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
					<dd>{dataset.org_name ?? 'Non renseignee'}</dd>
				</div>
				<div>
					<dt>Description</dt>
					<dd>{dataset.description ?? 'Non renseignee'}</dd>
				</div>
				<div>
					<dt>Licence</dt>
					<dd>{dataset.license ?? 'Non renseignee'}</dd>
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
				<a href={searchHref}>Retour a la recherche</a>
				{#if orgFilterLink}
					<a href={orgFilterLink}>Voir les datasets de cette organisation</a>
				{/if}
			</nav>
		{/if}
	</Card>
</section>

<style>
	.stack {
		display: grid;
		gap: var(--space-4);
	}

	h3.title {
		margin: 0;
		line-height: var(--line-height-title);
		font-size: clamp(1.2rem, 1.2vw + 1rem, 1.7rem);
	}

	.access-modes {
		margin-top: var(--space-4);
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
		margin: var(--space-4) 0 0;
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

	@media (max-width: 43.75rem) {
		.links {
			display: grid;
			gap: var(--space-3);
		}
	}

</style>