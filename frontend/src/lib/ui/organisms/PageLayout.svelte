<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * Layout de page standard — grille verticale avec gap cohérent.
	 * Factorise le pattern `.stack { display: grid; gap: var(--space-4); }`
	 * utilisé par toutes les pages de contenu.
	 */
	let { children, as = 'section', gap = 'var(--space-4)' }: {
		children: Snippet;
		as?: 'section' | 'main' | 'div';
		gap?: string;
	} = $props();
</script>

{#if as === 'main'}
	<main class="page-layout" style="gap: {gap}">
		{@render children()}
	</main>
{:else if as === 'div'}
	<div class="page-layout" style="gap: {gap}">
		{@render children()}
	</div>
{:else}
	<section class="page-layout" style="gap: {gap}">
		{@render children()}
	</section>
{/if}

<style>
	.page-layout {
		display: grid;
		gap: var(--space-4);
	}
</style>
