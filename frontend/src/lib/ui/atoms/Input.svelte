<script lang="ts">
	let {
		id,
		label,
		placeholder = '',
		value = $bindable(''),
		required = false,
		oninput,
		...restProps
	}: {
		id: string;
		label: string;
		placeholder?: string;
		value?: string;
		required?: boolean;
		oninput?: (event: Event) => void;
		[key: string]: unknown;
	} = $props();
</script>

<label class="field" for={id}>
	<span>{label}</span>
	<input {id} {placeholder} bind:value {required} {oninput} {...restProps} />
</label>

<style>
	.field {
		display: grid;
		gap: var(--space-2);
		font-size: var(--font-size-ui);
	}

	span {
		font-weight: 600;
		color: var(--color-on-surface-subtle);
	}

	input {
		border: var(--border-thin) solid var(--color-border);
		background: var(--color-surface);
		border-radius: var(--radius-none);
		padding: var(--space-3) var(--space-4);
		min-height: var(--size-control-md);
		color: var(--color-on-surface);
	}

	input:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}
</style>
