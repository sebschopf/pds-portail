<script lang="ts">
	import Skeleton from '$lib/ui/atoms/Skeleton.svelte';

	/**
	 * Squelette pour les cartes dataset, dimensions alignées avec CardDataset.
	 *
	 * Évite le CLS en reproduisant la structure visuelle d'une carte dataset
	 * (titre, méta, description, métriques, formats, tags, liens).
	 * Utilise Skeleton avec variant='text' pour les lignes de texte.
	 */
</script>

<article class="dataset-skeleton" role="status" aria-live="polite" aria-label="Chargement de la fiche dataset">
	<div class="skeleton-head">
		<Skeleton width="75%" height="1.5em" variant="text" />
		<Skeleton width="40%" height="1em" variant="text" />
	</div>

	<Skeleton width="90%" height="1em" variant="text" />
	<Skeleton width="60%" height="1em" variant="text" />

	<div class="skeleton-metrics">
		<div class="skeleton-metric">
			<Skeleton width="5em" height="0.875em" variant="text" />
			<Skeleton width="3em" height="1.25em" variant="text" />
		</div>
		<div class="skeleton-metric">
			<Skeleton width="6em" height="0.875em" variant="text" />
			<Skeleton width="3em" height="1.25em" variant="text" />
		</div>
		<div class="skeleton-metric">
			<Skeleton width="7em" height="0.875em" variant="text" />
			<Skeleton width="3em" height="1.25em" variant="text" />
		</div>
		<div class="skeleton-metric">
			<Skeleton width="5em" height="0.875em" variant="text" />
			<Skeleton width="2em" height="1.25em" variant="text" />
		</div>
	</div>

	<Skeleton width="70%" height="1em" variant="text" />
	<Skeleton width="50%" height="1em" variant="text" />

	<div class="skeleton-links">
		<Skeleton width="12em" height="1em" variant="text" />
		<Skeleton width="14em" height="1em" variant="text" />
	</div>
</article>

<style>
	.dataset-skeleton {
		display: grid;
		gap: var(--space-3);
		background: var(--color-surface);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		padding: var(--space-4);
	}

	.skeleton-head {
		display: grid;
		gap: var(--space-1);
	}

	.skeleton-metrics {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
		gap: var(--space-2);
	}

	.skeleton-metric {
		display: grid;
		gap: var(--space-1);
	}

	.skeleton-links {
		display: grid;
		gap: var(--space-1);
	}
</style>