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
 *
 * Permissions-Policy : contient uniquement les features standard
 * (supportées sans flag par Chromium ≥120, Firefox ≥120, Safari ≥17).
 * Source : https://github.com/w3c/webappsec-permissions-policy/blob/main/features.md
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

	// Permissions-Policy : désactiver les features non utilisées
	// Uniquement les features reconnues par défaut (pas de flag expérimental)
	response.headers.set(
		'Permissions-Policy',
		[
			'accelerometer=()',
			'autoplay=()',
			'camera=()',
			'cross-origin-isolated=()',
			'display-capture=()',
			'encrypted-media=()',
			'fullscreen=()',
			'geolocation=()',
			'gyroscope=()',
			'keyboard-map=()',
			'magnetometer=()',
			'microphone=()',
			'midi=()',
			'payment=()',
			'picture-in-picture=()',
			'publickey-credentials-get=()',
			'screen-wake-lock=()',
			'sync-xhr=()',
			'usb=()',
			'xr-spatial-tracking=()'
		].join(', ')
	);

	return response;
};