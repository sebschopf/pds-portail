<script lang="ts">
	import type { Snippet } from 'svelte';
	import EmptyIcon from '$lib/assets/icons/EmptyIcon.svelte';
	import ErrorIcon from '$lib/assets/icons/ErrorIcon.svelte';

	/**
	 * État vide ou d'erreur illustré — conforme au guide rédactionnel §3.1/§3.2/§6.
	 *
	 * Structure : Icône + Titre + Description + [Action optionnelle]
	 */
	let {
		variant = 'empty',
		title,
		description,
		iconSize = 'var(--icon-size-lg)',
		action
	}: {
		variant?: 'empty' | 'error';
		title: string;
		description: string;
		iconSize?: string;
		action?: Snippet;
	} = $props();

	const iconComponent = $derived(variant === 'error' ? ErrorIcon : EmptyIcon);
	const iconLabel = $derived(variant === 'error' ? 'Erreur' : 'Aucun résultat');
</script>

<div class="empty-state" role={variant === 'error' ? 'alert' : 'status'} aria-live="polite">
	<div class="empty-icon" aria-hidden="true">
		<iconComponent size={iconSize} label={iconLabel}></iconComponent>
	</div>
	<h2 class="empty-title">{title}</h2>
	<p class="empty-description">{description}</p>
	{#if action}
		<div class="empty-action">
			{@render action()}
		</div>
	{/if}
</div>

<style>
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		padding: var(--space-8) var(--space-4);
		gap: var(--space-3);
		background: var(--color-surface-muted);
		border: var(--border-thick) dashed var(--color-border);
		border-radius: var(--radius-none);
	}

	.empty-icon {
		color: var(--color-on-surface-soft);
		margin-bottom: var(--space-2);
	}

	.empty-title {
		margin: 0;
		font-size: var(--font-size-heading-md);
		line-height: var(--line-height-title);
		color: var(--color-on-surface);
		font-weight: 700;
	}

	.empty-description {
		margin: 0;
		max-width: 42ch;
		font-size: var(--font-size-body);
		line-height: var(--line-height-copy);
		color: var(--color-on-surface-soft);
	}

	.empty-action {
		margin-top: var(--space-3);
	}
</style>