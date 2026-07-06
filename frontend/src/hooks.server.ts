import type { Handle } from '@sveltejs/kit';
import { timingSafeEqual } from 'node:crypto';

function safeEquals(left: string, right: string): boolean {
	const leftBuffer = Buffer.from(left, 'utf-8');
	const rightBuffer = Buffer.from(right, 'utf-8');
	if (leftBuffer.length !== rightBuffer.length) {
		return false;
	}
	return timingSafeEqual(leftBuffer, rightBuffer);
}

function parseBasicAuthorizationHeader(header: string | null): { username: string; password: string } | null {
	if (!header) {
		return null;
	}

	const [scheme, encodedCredentials] = header.split(' ');
	if (scheme?.toLowerCase() !== 'basic' || !encodedCredentials) {
		return null;
	}

	try {
		const decoded = Buffer.from(encodedCredentials, 'base64').toString('utf-8');
		const separatorIndex = decoded.indexOf(':');
		if (separatorIndex < 0) {
			return null;
		}

		return {
			username: decoded.slice(0, separatorIndex),
			password: decoded.slice(separatorIndex + 1)
		};
	} catch {
		return null;
	}
}

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
	if (event.url.pathname.startsWith('/support')) {
		const supportUsername = process.env.SUPPORT_INTERNAL_USERNAME;
		const supportPassword = process.env.SUPPORT_INTERNAL_PASSWORD;

		if (!supportUsername || !supportPassword) {
			return new Response('Support access not configured', { status: 503 });
		}

		const credentials = parseBasicAuthorizationHeader(event.request.headers.get('Authorization'));
		const isAuthorized =
			credentials !== null &&
			safeEquals(credentials.username, supportUsername) &&
			safeEquals(credentials.password, supportPassword);

		if (!isAuthorized) {
			return new Response('Unauthorized', {
				status: 401,
				headers: {
					'WWW-Authenticate': 'Basic realm="Support Interne"'
				}
			});
		}
	}

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