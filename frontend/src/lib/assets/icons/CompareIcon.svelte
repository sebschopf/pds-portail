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
	<path d="M16,11 l2,2 5.2-5.2L18,2.6 15.5,4.5 18.2,7H3v2.1h14.7Z" />
	<path d="M8.8,13.5 l-2-2L1.6,17.2 6.4,22.5l2-2L6.2,18.3H21v-2.1H6.2Z" />
</svg>
