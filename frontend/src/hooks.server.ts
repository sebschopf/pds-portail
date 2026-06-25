import type { Handle } from '@sveltejs/kit';

/**
 * La CSP est désormais gérée de manière déclarative via svelte.config.ts
 * (kit.csp.mode: 'nonce'). Ce hook reste disponible pour d'autres usages
 * futurs (auth, logging, etc.).
 */
export const handle: Handle = async ({ event, resolve }) => {
	const response = await resolve(event);
	return response;
};
