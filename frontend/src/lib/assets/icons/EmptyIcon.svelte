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
	<rect x="3" y="5" width="18" height="14" />
	<line x1="3" y1="5" x2="12" y2="12" />
	<line x1="21" y1="5" x2="12" y2="12" />
	<line x1="7" y1="9" x2="7" y2="15" />
	<line x1="17" y1="9" x2="17" y2="15" />
</svg>
