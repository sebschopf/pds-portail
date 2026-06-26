import type { Handle } from '@sveltejs/kit';

/**
 * Security headers (PDS-38, ADR-021).
 *
 * La CSP est gérée de manière déclarative via svelte.config.ts
 * (kit.csp.mode: 'nonce'). Ce hook ajoute les headers restants :
 *   - Strict-Transport-Security (HSTS)
 *   - X-Content-Type-Options
 *   - Cross-Origin-Opener-Policy (COOP)
 *   - Referrer-Policy
 *   - Permissions-Policy
 *
 * X-Frame-Options n'est pas injecté ici car la CSP contient déjà
 * `frame-ancestors 'none'` qui est strictement supérieur.
 */
export const handle: Handle = async ({ event, resolve }) => {
	const response = await resolve(event);

	// HSTS : 1 an, inclure sous-domaines
	response.headers.set(
		'Strict-Transport-Security',
		'max-age=31536000; includeSubDomains'
	);

	// Anti-MIME sniffing
	response.headers.set('X-Content-Type-Options', 'nosniff');

	// Isolement du contexte de navigation
	response.headers.set('Cross-Origin-Opener-Policy', 'same-origin');

	// Referrer-Policy : ne leak que l'origine en cross-origin
	response.headers.set(
		'Referrer-Policy',
		'strict-origin-when-cross-origin'
	);

	// Permissions-Policy : désactiver tout ce qui n'est pas utilisé
	response.headers.set(
		'Permissions-Policy',
		[
			'accelerometer=()',
			'ambient-light-sensor=()',
			'autoplay=()',
			'battery=()',
			'camera=()',
			'cross-origin-isolated=()',
			'display-capture=()',
			'document-domain=()',
			'encrypted-media=()',
			'execution-while-not-rendered=()',
			'execution-while-out-of-viewport=()',
			'fullscreen=()',
			'geolocation=()',
			'gyroscope=()',
			'keyboard-map=()',
			'magnetometer=()',
			'microphone=()',
			'midi=()',
			'navigation-override=()',
			'payment=()',
			'picture-in-picture=()',
			'publickey-credentials-get=()',
			'screen-wake-lock=()',
			'sync-xhr=()',
			'usb=()',
			'web-share=()',
			'xr-spatial-tracking=()'
		].join(', ')
	);

	return response;
};
