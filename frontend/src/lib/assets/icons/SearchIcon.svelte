<script lang="ts">
	let { size = 'var(--icon-size-md)', class: className = '', label = 'Rechercher' }: {
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
	<circle cx="11" cy="11" r="7" />
	<line x1="16" y1="16" x2="21" y2="21" />
</svg>
