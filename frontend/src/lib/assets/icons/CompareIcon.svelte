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
	<g transform="translate(4,4)">
		<path d="M10.08,7 l1,1 3.44-3.45L11,1 10,2 l1.8,1.8H2v1.4h9.82Z" />
		<path d="M5.86,9 l-1-1L1.42,11.5 4.91,15l1-1L4.1,12.2H14V10.8H4.1Z" />
	</g>
</svg>
