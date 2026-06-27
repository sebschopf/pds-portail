<script lang="ts">
	let { size = 'var(--icon-size-md)', class: className = '', label = 'Comparer' }: {
		size?: string;
		class?: string;
		label?: string;
	} = $props();
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="3"
	stroke-linecap="round"
	stroke-linejoin="round"
	class={className}
	aria-label={label}
	role="img"
>
	<polyline points="8,6 4,10 8,14" />
	<line x1="4" y1="10" x2="16" y2="10" />
	<polyline points="16,18 20,14 16,10" />
	<line x1="20" y1="14" x2="8" y2="14" />
</svg>
