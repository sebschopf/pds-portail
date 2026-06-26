<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		title,
		subtitle = '',
		children
	}: {
		title: string;
		subtitle?: string;
		children?: Snippet;
	} = $props();
</script>

<article class="card" role="group" aria-label={title}>
	<header>
		<h2>{title}</h2>
		{#if subtitle}
			<p>{subtitle}</p>
		{/if}
	</header>
	{#if children}
		{@render children()}
	{/if}
</article>

<style>
	.card {
		background: var(--color-surface);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
		padding: var(--space-4);
		box-shadow: var(--shadow-soft);
	}

	h2 {
		margin: 0;
		font-size: var(--font-size-heading-lg);
		line-height: var(--line-height-title);
	}

	p {
		margin: var(--space-1) 0 0;
		color: var(--color-on-surface-muted);
		font-size: var(--font-size-ui);
	}

	header {
		margin-bottom: var(--space-3);
	}
</style>
