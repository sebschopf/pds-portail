<script lang="ts">
	let { size = 'var(--icon-size-md)', class: className = '', label = 'Aucun résultat' }: {
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
	<polygon points="2,10 12,4 22,10 12,16" />
	<polygon points="2,10 2,20 12,24 12,16" />
	<polygon points="22,10 22,20 12,24 12,16" />
	<polyline points="4,12 4,18" />
	<polyline points="20,12 20,18" />
</svg>
