<script lang="ts">
	let { size = 'var(--icon-size-md)', class: className = '', label = 'Jeu de données' }: {
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
	<rect x="2" y="3" width="20" height="5" />
	<rect x="2" y="10" width="20" height="5" />
	<rect x="2" y="17" width="20" height="5" />
	<line x1="6" y1="3" x2="6" y2="22" />
</svg>
