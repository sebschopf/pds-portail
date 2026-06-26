import adapter from '@sveltejs/adapter-auto';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

// Garde-fou build : PUBLIC_USE_MOCK_API=1 interdit en production.
// Si cette variable est activée lors d'un build de production, on bloque immédiatement.
if (process.env.NODE_ENV === 'production' && process.env.PUBLIC_USE_MOCK_API === '1') {
	throw new Error(
		'[SECURITE] PUBLIC_USE_MOCK_API=1 est interdit en production. ' +
			'Retirer cette variable avant de lancer "npm run build".'
	);
}

const apiTarget = process.env.PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000';
const useMockApi = process.env.PUBLIC_USE_MOCK_API === '1';

export default defineConfig({
	test: {
		environment: 'node',
		include: ['src/**/*.test.ts']
	},
	server: {
		proxy: useMockApi
			? undefined
			: {
					'/api': {
						target: apiTarget,
						changeOrigin: true
					}
				}
	},
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			// adapter-auto détecte automatiquement Vercel en production
			// et utilise un adaptateur local en développement
			adapter: adapter()
		})
	]
});