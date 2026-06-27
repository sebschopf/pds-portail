<script lang="ts">
	import type { DatasetStructureContract } from '$lib/contracts/dataset-detail';

	let {
		structure
	}: {
		structure: DatasetStructureContract;
	} = $props();

	const hasData = $derived(
		structure.fields.length > 0 ||
			structure.formats.length > 0 ||
			structure.update_frequency !== null ||
			structure.last_updated !== null
	);

	const fieldCount = $derived(structure.fields.length);
	const formatCount = $derived(structure.formats.length);

	const fieldLabel = $derived.by(() => {
		if (fieldCount === 0) return 'Aucun champ decrit';
		if (fieldCount === 1) return '1 champ';
		return `${fieldCount} champs`;
	});

	const formatLabel = $derived.by(() => {
		if (formatCount === 0) return 'Aucun format';
		if (formatCount === 1) return '1 format';
		return `${formatCount} formats`;
	});
</script>

<section class="structure-block" aria-label="Structure du dataset">
	<h3 class="structure-heading">Structure du jeu de donnees</h3>

	{#if hasData}
		<div class="structure-grid">
			{#if structure.fields.length > 0}
				<article class="structure-item" aria-label="Champs du dataset">
					<h4 class="item-title">Champs disponibles</h4>
					<p class="item-count">{fieldLabel}</p>
					<ul class="field-list" aria-label="Liste des champs">
						{#each structure.fields as field, idx (`${field}-${idx}`)}
							<li>{field}</li>
						{/each}
					</ul>
				</article>
			{/if}

			<div class="structure-meta">
				{#if structure.formats.length > 0}
					<article class="meta-item" aria-label="Formats disponibles">
						<h4 class="meta-title">Formats de fichier</h4>
						<ul class="format-list">
							{#each structure.formats as fmt, idx (`${fmt}-${idx}`)}
								<li class="format-badge">{fmt}</li>
							{/each}
						</ul>
					</article>
				{/if}

				{#if structure.update_frequency}
					<article class="meta-item" aria-label="Frequence de mise a jour">
						<h4 class="meta-title">Frequence de mise a jour</h4>
						<p class="meta-value">{structure.update_frequency}</p>
					</article>
				{/if}

				{#if structure.last_updated}
					<article class="meta-item" aria-label="Derniere mise a jour">
						<h4 class="meta-title">Derniere mise a jour</h4>
						<p class="meta-value">{structure.last_updated}</p>
					</article>
				{/if}
			</div>
		</div>
	{:else}
		<p class="structure-empty" role="status">Structure du dataset non renseignee</p>
	{/if}
</section>

<style>
	.structure-block {
		margin-top: var(--space-5);
	}

	.structure-heading {
		margin: 0 0 var(--space-3);
		font-size: var(--font-size-heading-md);
		line-height: var(--line-height-title);
	}

	.structure-grid {
		display: grid;
		gap: var(--space-3);
	}

	.structure-empty {
		margin: 0;
		padding: var(--space-3) var(--space-4);
		background: var(--color-surface-muted);
		border: var(--border-thin) dashed var(--color-border);
		border-radius: var(--radius-none);
		color: var(--color-on-surface-soft);
	}

	.structure-item {
		padding: var(--space-4);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		background: var(--color-surface);
	}

	.item-title {
		margin: 0 0 var(--space-2);
		font-size: var(--font-size-ui);
		font-weight: 700;
		color: var(--color-on-surface-subtle);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.item-count {
		margin: 0 0 var(--space-2);
		font-size: var(--font-size-ui);
		color: var(--color-on-surface-muted);
	}

	.field-list {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}

	.field-list li {
		padding: var(--space-1) var(--space-2);
		background: var(--color-surface-muted);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		font-size: var(--font-size-ui);
		font-family: var(--font-mono, monospace);
		overflow-wrap: anywhere;
	}

	.structure-meta {
		display: grid;
		gap: var(--space-3);
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	}

	.meta-item {
		padding: var(--space-3);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		background: var(--color-surface);
	}

	.meta-title {
		margin: 0 0 var(--space-1);
		font-size: var(--font-size-ui);
		font-weight: 700;
		color: var(--color-on-surface-subtle);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.meta-value {
		margin: 0;
		font-size: var(--font-size-heading-sm);
		font-weight: 600;
	}

	.format-list {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1);
	}

	.format-badge {
		padding: var(--space-1) var(--space-3);
		background: color-mix(in oklch, var(--color-primary) 10%, var(--color-surface));
		border: var(--border-thin) solid var(--color-primary);
		border-radius: var(--radius-none);
		font-size: var(--font-size-ui);
		font-weight: 700;
		font-family: var(--font-mono, monospace);
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}
</style>