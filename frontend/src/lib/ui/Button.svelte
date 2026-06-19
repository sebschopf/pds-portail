<script lang="ts">
	let {
		label,
		type = 'button',
		variant = 'primary',
		disabled = false,
		onclick
	}: {
		label: string;
		type?: 'button' | 'submit';
		variant?: 'primary' | 'ghost';
		disabled?: boolean;
		onclick?: () => void;
	} = $props();
</script>

<button class={`btn ${variant}`} {type} {disabled} {onclick}>
	{label}
</button>

<style>
	.btn {
		border: var(--border-thin) solid transparent;
		border-radius: var(--radius-none);
		padding: var(--space-3) var(--space-4);
		min-height: var(--size-control-lg);
		font-weight: 650;
		cursor: pointer;
		transition: transform 140ms ease, background-color 140ms ease, border-color 140ms ease;
	}

	.btn:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	.btn:active {
		transform: translateY(1px);
	}

	.primary {
		background: var(--color-primary);
		color: var(--color-on-primary);
	}

	.primary:hover {
		background: var(--color-secondary);
	}

	.ghost {
		background: transparent;
		border-color: var(--color-border);
		color: var(--color-on-surface);
	}

	.ghost:hover {
		background: var(--color-surface-muted);
	}

	.btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
