import { describe, expect, it } from 'vitest';

import {
	isDatasetDetailContract,
	isDatasetStructureContract,
	isResourceContract
} from './dataset-detail';

describe('isDatasetStructureContract', () => {
	const validStructure = {
		fields: ['Nom', 'Prenom', 'Age'],
		formats: ['CSV', 'JSON'],
		update_frequency: 'Annuelle',
		last_updated: '2026-01-15'
	};

	it('valide une structure complete', () => {
		expect(isDatasetStructureContract(validStructure)).toBe(true);
	});

	it('valide une structure avec listes vides', () => {
		expect(
			isDatasetStructureContract({
				fields: [],
				formats: [],
				update_frequency: null,
				last_updated: null
			})
		).toBe(true);
	});

	it('rejette un payload non-objet', () => {
		expect(isDatasetStructureContract(null)).toBe(false);
		expect(isDatasetStructureContract('texte')).toBe(false);
	});

	it('rejette un objet sans fields', () => {
		expect(
			isDatasetStructureContract({
				formats: ['CSV'],
				update_frequency: null,
				last_updated: null
			})
		).toBe(false);
	});

	it('rejette fields non-array', () => {
		expect(
			isDatasetStructureContract({
				fields: 'pas-un-array',
				formats: ['CSV'],
				update_frequency: null,
				last_updated: null
			})
		).toBe(false);
	});

	it('rejette fields avec elements non-string', () => {
		expect(
			isDatasetStructureContract({
				fields: ['Nom', 42],
				formats: ['CSV'],
				update_frequency: null,
				last_updated: null
			})
		).toBe(false);
	});
});

describe('isDatasetDetailContract', () => {
	const defaultStructure = {
		fields: ['Nom', 'Prenom'],
		formats: ['CSV'],
		update_frequency: 'Annuelle',
		last_updated: '2026-01-15'
	};

	const defaultResources = [
		{
			id: 'resource-1',
			name: 'Ressource principale',
			format: 'CSV',
			url: 'https://example.com/resource.csv',
			size_bytes: 1024,
			created: '2026-01-01',
			last_modified: '2026-01-05'
		}
	];

	it('valide un payload conforme au contrat backend dataset avec structure', () => {
		const payload = {
			id: 'dataset-1',
			title: 'Dataset transport',
			description: 'Description lisible',
			org_id: 'org-1',
			org_name: 'Office statistique',
			license: 'OGL',
			quality_score: 85,
			completeness: 80,
			freshness_days: 12,
			resources: defaultResources,
			dataset_structure: defaultStructure
		};

		expect(isDatasetDetailContract(payload)).toBe(true);
	});

	it('rejette un payload sans champs obligatoires', () => {
		const payload = {
			id: 'dataset-1',
			title: 'Dataset transport'
		};

		expect(isDatasetDetailContract(payload)).toBe(false);
	});

	it('valide explicitement les champs nullable a null', () => {
		const payload = {
			id: 'dataset-1',
			title: 'Dataset transport',
			description: null,
			org_id: null,
			org_name: null,
			license: null,
			quality_score: null,
			completeness: null,
			freshness_days: null,
			resources: [],
			dataset_structure: {
				fields: [],
				formats: [],
				update_frequency: null,
				last_updated: null
			}
		};

		expect(isDatasetDetailContract(payload)).toBe(true);
	});

	it('rejette les types invalides sur les champs textuels', () => {
		const payload = {
			id: 123,
			title: 'Dataset transport',
			description: 'Description',
			org_id: 'org-1',
			org_name: 'Office statistique',
			license: 'OGL'
		};

		expect(isDatasetDetailContract(payload)).toBe(false);
	});

	it('rejette un payload avec dataset_structure invalide', () => {
		const payload = {
			id: 'dataset-1',
			title: 'Dataset transport',
			description: 'Description',
			org_id: 'org-1',
			org_name: 'Office statistique',
			license: 'OGL',
			quality_score: 85,
			completeness: 80,
			freshness_days: 12,
			resources: defaultResources,
			dataset_structure: { fields: 'invalide', formats: ['CSV'], update_frequency: null, last_updated: null }
		};

		expect(isDatasetDetailContract(payload)).toBe(false);
	});

	it('rejette un payload sans resources', () => {
		const payload = {
			id: 'dataset-1',
			title: 'Dataset transport',
			description: 'Description',
			org_id: 'org-1',
			org_name: 'Office statistique',
			license: 'OGL',
			quality_score: 85,
			completeness: 80,
			freshness_days: 12,
			dataset_structure: defaultStructure
		};

		expect(isDatasetDetailContract(payload)).toBe(false);
	});
});

describe('isResourceContract', () => {
	it('valide une ressource conforme', () => {
		expect(
			isResourceContract({
				id: 'resource-1',
				name: 'Ressource principale',
				format: 'CSV',
				url: 'https://example.com/resource.csv',
				size_bytes: 2048,
				created: '2026-01-01',
				last_modified: '2026-01-05'
			})
		).toBe(true);
	});

	it('rejette une ressource invalide', () => {
		expect(
			isResourceContract({
				id: 'resource-1',
				name: 42,
				format: 'CSV',
				url: 'https://example.com/resource.csv',
				size_bytes: 2048,
				created: '2026-01-01',
				last_modified: '2026-01-05'
			})
		).toBe(false);
	});
});