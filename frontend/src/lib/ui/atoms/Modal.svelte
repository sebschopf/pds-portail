<script lang="ts">
	import { onMount } from 'svelte';

	let { open = false, title, onclose, children }: { open: boolean; title: string; onclose?: () => void; children?: any } = $props();

	let dialogElement: HTMLDialogElement;
	let previouslyFocusedElement: HTMLElement | null = null;

	onMount(() => {
		if (open) {
			dialogElement?.showModal();
			previouslyFocusedElement = document.activeElement as HTMLElement;
		}

		const handleEsc = (e: KeyboardEvent) => {
			if (e.key === 'Escape') {
				handleClose();
			}
		};

		if (dialogElement) {
			dialogElement.addEventListener('keydown', handleEsc);
		}

		return () => {
			if (dialogElement) {
				dialogElement.removeEventListener('keydown', handleEsc);
			}
		};
	});

	$effect(() => {
		if (open && dialogElement) {
			dialogElement.showModal();
			previouslyFocusedElement = document.activeElement as HTMLElement;
		} else if (!open && dialogElement?.open) {
			dialogElement.close();
			previouslyFocusedElement?.focus();
		}
	});

	function handleClose() {
		if (dialogElement?.open) {
			dialogElement.close();
		}
		onclose?.();
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === dialogElement) {
			handleClose();
		}
	}
</script>

<dialog
	bind:this={dialogElement}
	class="modal-dialog"
	aria-modal="true"
	aria-labelledby="modal-title"
	onclose={handleClose}
	onclick={handleBackdropClick}
>
	<div class="modal-content">
		<button class="modal-close" onclick={handleClose} aria-label="Fermer la modale">
			<span aria-hidden="true">×</span>
		</button>
		<h2 id="modal-title" class="modal-title">{title}</h2>
		<div class="modal-body">
			{@render children?.()}
		</div>
	</div>
</dialog>

<style>
	.modal-dialog {
		border: none;
		border-radius: var(--radius-none);
		padding: 0;
		max-width: 90%;
		width: 500px;
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
		background: var(--color-surface);
		color: var(--color-on-surface);
	}

	.modal-dialog::backdrop {
		background: rgba(0, 0, 0, 0.5);
		animation: fadeIn 200ms ease;
	}

	.modal-content {
		position: relative;
		padding: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.modal-close {
		position: absolute;
		top: var(--space-3);
		right: var(--space-3);
		width: 32px;
		height: 32px;
		padding: 0;
		border: none;
		background: transparent;
		color: var(--color-on-surface);
		font-size: var(--font-size-display-metric);
		cursor: pointer;
		border-radius: var(--radius-none);
		display: flex;
		align-items: center;
		justify-content: center;
		transition: background-color 140ms ease;
	}

	.modal-close:hover {
		background: var(--color-surface-muted);
	}

	.modal-close:focus-visible {
		outline: var(--outline-focus) solid var(--color-focus-ring);
		outline-offset: var(--outline-offset);
	}

	.modal-title {
		margin: 0;
		font-size: var(--font-size-display-metric);
		font-weight: 700;
		padding-right: var(--space-4);
	}

	.modal-body {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	/* Mobile adaptation */
	@media (max-width: 40rem) {
		.modal-dialog {
			width: 95vw;
			max-width: 95vw;
		}

		.modal-content {
			padding: var(--space-4);
		}

		.modal-title {
			font-size: clamp(1.1rem, 1.25rem, 1.5rem);
		}
	}
</style>
