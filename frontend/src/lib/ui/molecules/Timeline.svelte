<script lang="ts">
	/**
	 * Timeline — Molécule de chronologie.
	 * Affiche une liste verticale d'étapes avec marqueurs colorés (done/current/upcoming).
	 * Utilisé par la page /suite pour le calendrier prévisionnel.
	 */
	interface TimelineStep {
		date: string;
		label: string;
		detail: string;
		state: 'done' | 'current' | 'upcoming';
	}

	let { steps, ariaLabel = 'Chronologie' }: {
		steps: TimelineStep[];
		ariaLabel?: string;
	} = $props();

	const markerSymbol: Record<string, string> = {
		done: '✓',
		current: '●',
		upcoming: '○'
	};
</script>

<div class="timeline" role="list" aria-label={ariaLabel}>
	{#each steps as step}
		<div class="timeline-item" role="listitem">
			<div
				class="timeline-marker {step.state}"
				aria-hidden="true"
			>
				{markerSymbol[step.state]}
			</div>
			<div class="timeline-body">
				<span class="timeline-date">{step.date}</span>
				<span class="timeline-label">{step.label}</span>
				<span class="timeline-detail">{step.detail}</span>
			</div>
		</div>
	{/each}
</div>

<style>
	.timeline {
		margin: var(--space-4) 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.timeline-item {
		display: flex;
		gap: var(--space-3);
		align-items: flex-start;
	}

	.timeline-marker {
		flex-shrink: 0;
		width: 1.5em;
		height: 1.5em;
		border-radius: var(--radius-none);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: var(--font-size-caption);
		font-weight: 700;
		border: var(--border-strong) solid var(--color-border);
		margin-top: 0.1em;
	}

	.timeline-marker.done {
		background: var(--color-success);
		border-color: var(--color-success);
		color: oklch(1 0 0);
	}

	.timeline-marker.current {
		background: var(--color-primary);
		border-color: var(--color-primary);
		color: oklch(1 0 0);
		animation: timeline-pulse 2s ease-in-out infinite;
	}

	.timeline-marker.upcoming {
		background: var(--color-surface);
		border-color: var(--color-border);
		color: var(--color-on-surface-subtle);
	}

	.timeline-body {
		display: flex;
		flex-direction: column;
		gap: var(--space-0);
	}

	.timeline-date {
		font-size: var(--font-size-caption);
		font-weight: 700;
		color: var(--color-primary);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.timeline-label {
		font-size: var(--font-size-ui);
		font-weight: 650;
		color: var(--color-on-surface);
	}

	.timeline-detail {
		font-size: var(--font-size-caption);
		color: var(--color-on-surface-muted);
	}

	@keyframes timeline-pulse {
		0%, 100% { box-shadow: 0 0 0 0 oklch(0.5119 0.1301 239 / 0.4); }
		50% { box-shadow: 0 0 0 6px oklch(0.5119 0.1301 239 / 0); }
	}

	@media (prefers-reduced-motion: reduce) {
		.timeline-marker.current {
			animation: none;
		}
	}
</style>