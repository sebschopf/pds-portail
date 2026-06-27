<script lang="ts">
	let { size = 'var(--icon-size-md)', class: className = '', label = 'Erreur' }: {
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
	<polygon points="12,2 22,22 2,22" />
	<line x1="12" y1="10" x2="12" y2="16" />
	<line x1="12" y1="18" x2="12.01" y2="18" stroke-width="3" />
</svg>
