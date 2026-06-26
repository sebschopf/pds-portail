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
	stroke-width="2.5"
	stroke-linecap="square"
	stroke-linejoin="miter"
	class={className}
	aria-label={label}
	role="img"
>
	<polygon points="2,4 14,14 14,22 10,20 10,14 2,4" />
	<line x1="18" y1="8" x2="22" y2="8" />
	<line x1="20" y1="6" x2="20" y2="10" />
</svg>
