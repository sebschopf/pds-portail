<script lang="ts">
	export type BreadcrumbItem = {
		label: string;
		href?: string;
	};

	let {
		items,
		ariaLabel = "Fil d'Ariane"
	}: {
		items: BreadcrumbItem[];
		ariaLabel?: string;
	} = $props();
</script>

{#if items.length > 0}
	<nav class="breadcrumb" aria-label={ariaLabel}>
		<ol>
			{#each items as item, index (`${item.label}-${index}`)}
				<li>
					{#if item.href && index < items.length - 1}
						<a href={item.href}>{item.label}</a>
					{:else}
						<span aria-current="page">{item.label}</span>
					{/if}
				</li>
			{/each}
		</ol>
	</nav>
{/if}

<style>
	.breadcrumb ol {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		font-size: var(--font-size-ui);
	}

	.breadcrumb li {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
	}

	.breadcrumb li:not(:last-child)::after {
		content: '/';
		color: var(--color-on-surface-muted);
	}

	.breadcrumb a {
		text-decoration-thickness: var(--border-strong);
		overflow-wrap: anywhere;
	}

	.breadcrumb span {
		color: var(--color-on-surface-subtle);
		font-weight: 600;
		overflow-wrap: anywhere;
	}
</style>
