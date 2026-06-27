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
	<path d="M2,3h5v12H2z M4,5h1v8H4z" />
	<path d="M17,9v12h5V9H17z M20,11h1v8h-1z" />
	<path d="M12,3l4,4l-4,4V8H9V6h3V3z" />
	<path d="M12,16h3v2h-3v3l-4-4l4-4V16z" />
</svg>
