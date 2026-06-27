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
	<path d="M4 2h16v20H4z" />
	<line x1="8" y1="7" x2="18" y2="7" />
	<line x1="8" y1="11" x2="18" y2="11" />
	<line x1="8" y1="15" x2="18" y2="15" />
	<line x1="8" y1="19" x2="16" y2="19" />
</svg>
