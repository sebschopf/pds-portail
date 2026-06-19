<script lang="ts">
	let {
		label,
		variant = 'info'
	}: {
		label: string;
		variant?: 'info' | 'success' | 'warning' | 'danger';
	} = $props();
</script>

<span class={`badge ${variant}`} role="status">{label}</span>

<style>
	.badge {
		display: inline-flex;
		align-items: center;
		padding: var(--space-1) var(--space-3);
		border-radius: var(--radius-none);
		font-size: var(--font-size-ui);
		font-weight: 650;
		border: var(--border-thin) solid var(--color-border);
		background: var(--color-surface-muted);
		color: var(--color-on-surface);
	}

	.success {
		background: var(--color-success);
		color: var(--color-on-success);
		border-color: var(--color-success);
	}

	.warning {
		background: var(--color-warning);
		color: var(--color-on-warning);
		border-color: var(--color-warning);
	}

	.danger {
		background: var(--color-danger);
		color: var(--color-on-danger);
		border-color: var(--color-danger);
	}

	.info {
		background: var(--color-primary);
		color: var(--color-on-primary);
		border-color: var(--color-primary);
	}
</style>
