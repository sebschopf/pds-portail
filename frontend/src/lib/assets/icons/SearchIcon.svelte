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
	stroke-width="2.5"
	stroke-linecap="square"
	stroke-linejoin="miter"
	class={className}
	aria-label={label}
	role="img"
>
	<circle cx="10" cy="10" r="7" />
	<line x1="15.5" y1="15.5" x2="22" y2="22" />
</svg>
