<script lang="ts">
	import { slide } from 'svelte/transition';
	import { Button } from '$lib';
	import CompareIcon from '../../assets/icons/CompareIcon.svelte';

	let {
		compareIds,
		onClear,
		onCompare
	}: {
		compareIds: string[];
		onClear: () => void;
		onCompare: () => void;
	} = $props();

	const count = $derived(compareIds.length);
	const label = $derived(
		count === 1 ? '1 dataset selectionne' : `${count} datasets selectionnes`
	);
	const canCompare = $derived(count >= 2);
</script>

{#if count > 0}
	<div transition:slide={{ duration: 300 }} class="compare-bar" role="status" aria-live="polite" aria-label="Barre de comparaison">
		<p class="compare-label">
			<CompareIcon size="var(--icon-size-md)" label="Comparer" />
			{label}
		</p>
		<div class="compare-actions">
			<Button
				label="Comparer"
				variant="primary"
				disabled={!canCompare}
				onclick={onCompare}
			/>
			<Button
				label="Vider"
				variant="ghost"
				onclick={onClear}
			/>
		</div>
	</div>
{/if}

<style>
	.compare-bar {
		position: sticky;
		bottom: 0;
		z-index: 100;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-4);
		background: var(--color-surface);
		border-top: var(--border-thin) solid var(--color-border);
		box-shadow: 0 -2px 8px oklch(0 0 0 / 0.1);
	}

	.compare-label {
		margin: 0;
		font-weight: 600;
		font-size: var(--font-size-heading-sm);
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.compare-actions {
		display: flex;
		gap: var(--space-2);
	}

	@media (max-width: 43.75rem) {
		.compare-bar {
			flex-direction: column;
			align-items: stretch;
			gap: var(--space-2);
		}

		.compare-actions {
			justify-content: flex-end;
		}
	}
</style>