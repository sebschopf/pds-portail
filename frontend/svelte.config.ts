import adapter from '@sveltejs/adapter-auto';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import type { Config } from '@sveltejs/kit';

const config: Config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// adapter-auto détecte Vercel automatiquement en production,
		// Vercel gère la redirection HTTPS (PDS-38)
		adapter: adapter(),

		csp: {
			mode: 'nonce',
			directives: {
				'default-src': ['self'],
				'script-src': ['self'],
				'style-src': ['self', 'unsafe-inline'],
				'connect-src': [
					'self',
					'https://pds-portail-backend.fly.dev',
					'https://opendata.swiss'
				],
				'img-src': ['self', 'https://opendata.swiss', 'data:'],
				'font-src': ['self'],
				'frame-ancestors': ['none'],
				'form-action': ['self'],
				'base-uri': ['self'],
				'object-src': ['none'],
				// Trusted Types (PDS-38) - trajectoire documentée, mode rapport
				'report-uri': ['/api/v1/csp-report']
			}
		},

		csrf: {
			// Allow cross-origin requests from the backend for API routes.
			// The frontend is served from Vercel, backend from Fly.io.
			checkOrigin: process.env.NODE_ENV === 'production'
		}
	}
};

export default config;