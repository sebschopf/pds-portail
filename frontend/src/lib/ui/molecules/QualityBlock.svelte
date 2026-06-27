<script lang="ts">
	let {
		quality_score,
		completeness,
		freshness_days
	}: {
		quality_score: number | null;
		completeness: number | null;
		freshness_days: number | null;
	} = $props();

	const qualityLabel = $derived.by(() => {
		if (quality_score === null) return 'Non renseigné';
		if (quality_score >= 70) return 'Bonne qualité';
		if (quality_score >= 40) return 'Qualité moyenne';
		return 'Qualité faible';
	});

	const qualityVariant = $derived.by(() => {
		if (quality_score === null) return 'none';
		if (quality_score >= 70) return 'good';
		if (quality_score >= 40) return 'medium';
		return 'low';
	});

	const freshnessText = $derived.by(() => {
		if (freshness_days === null) return 'Non renseignée';
		if (freshness_days === 1) return '1 jour';
		return `${freshness_days} jours`;
	});

	const freshnessLabel = $derived.by(() => {
		if (freshness_days === null) return 'Alerte';
		if (freshness_days <= 30) return 'Mise à jour récente';
		if (freshness_days <= 180) return 'Mise à jour modérée';
		return 'Données anciennes';
	});

	const freshnessVariant = $derived.by(() => {
		if (freshness_days === null) return 'low';
		if (freshness_days <= 30) return 'good';
		if (freshness_days <= 180) return 'medium';
		return 'low';
	});

	const completenessLabel = $derived.by(() => {
		if (completeness === null) return 'Non renseignée';
		if (completeness >= 80) return 'Complète';
		if (completeness >= 40) return 'Partiellement complète';
		return 'Peu complète';
	});

	const completenessVariant = $derived.by(() => {
		if (completeness === null) return 'none';
		if (completeness >= 80) return 'good';
		if (completeness >= 40) return 'medium';
		return 'low';
	});
</script>

<section class="quality-block" aria-label="Indicateurs qualité du dataset">
	<h3 class="quality-heading">Qualité du dataset</h3>

	<div class="quality-grid">
		<article class="quality-item {qualityVariant === 'low' ? 'quality-low' : qualityVariant === 'medium' ? 'quality-medium' : qualityVariant === 'good' ? 'quality-good' : ''}" aria-label="Score qualité: {qualityLabel}">
			<h4 class="item-title">Score qualité</h4>
			<p class="item-value">{quality_score ?? 'N/R'}</p>
			<p class="item-label">{qualityLabel}</p>
		</article>

		<article class="quality-item {completenessVariant === 'low' ? 'quality-low' : completenessVariant === 'medium' ? 'quality-medium' : completenessVariant === 'good' ? 'quality-good' : ''}" aria-label="Complétude: {completenessLabel}">
			<h4 class="item-title">Complétude</h4>
			<p class="item-value">{completeness !== null ? `${completeness}/100` : 'N/R'}</p>
			<p class="item-label">{completenessLabel}</p>
		</article>

		<article class="quality-item {freshnessVariant === 'low' ? 'quality-low' : freshnessVariant === 'medium' ? 'quality-medium' : freshnessVariant === 'good' ? 'quality-good' : ''}" aria-label="Fraîcheur: {freshnessLabel}">
			<h4 class="item-title">Fraîcheur</h4>
			<p class="item-value">{freshnessText}</p>
			<p class="item-label">{freshnessLabel}</p>
			{#if freshness_days !== null}
				<p class="item-detail">
					Dernière mise à jour il y a {freshnessText}
				</p>
			{/if}
		</article>
	</div>

	{#if quality_score !== null || completeness !== null || freshness_days !== null}
		<details class="quality-details">
			<summary>Pourquoi ce score ?</summary>
			<dl class="details-list">
				<div>
					<dt>Score qualité</dt>
					<dd>Calculé sur 5 dimensions (completude, fraicheur, formats standards, signal geo-temporel, nombre de ressources). Chaque dimension vaut 0, 0.5 ou 1, multiplie par 20.</dd>
				</div>
				<div>
					<dt>Complétude</dt>
					<dd>Vérification de 5 champs: description renseignée, tags non vides, date de création, date de modification, au moins 1 ressource.</dd>
				</div>
				<div>
					<dt>Fraîcheur</dt>
					<dd>Jours écoulés depuis la dernière mise à jour CKAN. Recent: moins de 30 jours, modere: moins de 180 jours, ancien: plus de 180 jours.</dd>
				</div>
			</dl>
		</details>
	{/if}
</section>

<style>
	.quality-block {
		margin-top: var(--space-5);
	}

	.quality-heading {
		margin: 0 0 var(--space-3);
		font-size: var(--font-size-heading-md);
		line-height: var(--line-height-title);
	}

	.quality-grid {
		display: grid;
		gap: var(--space-3);
		grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
	}

	.quality-item {
		padding: var(--space-4);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		display: grid;
		gap: var(--space-1);
	}

	.quality-item.quality-good {
		border-left: var(--border-strong) solid var(--color-success);
		background: color-mix(in oklch, var(--color-success) 8%, var(--color-surface));
	}

	.quality-item.quality-medium {
		border-left: var(--border-strong) solid var(--color-warning);
		background: color-mix(in oklch, var(--color-warning) 8%, var(--color-surface));
	}

	.quality-item.quality-low {
		border-left: var(--border-strong) solid var(--color-danger);
		background: color-mix(in oklch, var(--color-danger) 8%, var(--color-surface));
	}

	.item-title {
		margin: 0;
		font-size: var(--font-size-ui);
		font-weight: 700;
		color: var(--color-on-surface-subtle);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.item-value {
		margin: 0;
		font-size: var(--font-size-display-metric);
		font-weight: 800;
		line-height: var(--line-height-compact);
	}

	.item-label {
		margin: 0;
		font-size: var(--font-size-ui);
		color: var(--color-on-surface-soft);
	}

	.item-detail {
		margin: 0;
		font-size: var(--font-size-ui);
		color: var(--color-on-surface-muted);
	}

	.quality-details {
		margin-top: var(--space-4);
	}

	.quality-details summary {
		cursor: pointer;
		font-weight: 650;
		font-size: var(--font-size-ui);
	}

	.details-list {
		display: grid;
		gap: var(--space-3);
		margin: var(--space-3) 0 0;
		padding: var(--space-3);
		background: var(--color-surface-muted);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
	}

	.details-list div {
		display: grid;
		gap: var(--space-1);
	}

	.details-list dt {
		font-weight: 700;
		font-size: var(--font-size-ui);
	}

	.details-list dd {
		margin: 0;
		font-size: var(--font-size-ui);
		color: var(--color-on-surface-soft);
		line-height: var(--line-height-detail);
	}
</style>