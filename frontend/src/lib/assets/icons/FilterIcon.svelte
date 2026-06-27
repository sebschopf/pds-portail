<script lang="ts">
	let { size = 'var(--icon-size-md)', class: className = '', label = 'Filtrer' }: {
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
	<path d="M2 2H22V6L15 14V22H9V14L2 6V2Z" />
</svg>
