import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';

import Modal from '../../lib/ui/atoms/Modal.svelte';

describe('Modal (accessibilité WCAG AA)', () => {
	it('affiche le titre et les attributs ARIA requis pour une boîte de dialogue', () => {
		const view = render(Modal, {
			props: {
				open: true,
				title: 'Confirmation'
			}
		});

		expect(view.body).toContain('Confirmation');
		expect(view.body).toContain('aria-modal="true"');
		expect(view.body).toContain('aria-labelledby="modal-title"');
	});

	it('inclut un bouton de fermeture avec aria-label accessible', () => {
		const view = render(Modal, {
			props: {
				open: true,
				title: 'Test'
			}
		});

		expect(view.body).toContain('aria-label="Fermer la modale"');
	});
});
