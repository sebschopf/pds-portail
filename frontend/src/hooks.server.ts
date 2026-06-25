import type { Handle } from '@sveltejs/kit';
import crypto from 'node:crypto';

const buildCsp = (nonce: string): string =>
	[
		"default-src 'self'",
		`script-src 'self' 'nonce-${nonce}'`,
		"style-src 'self' 'unsafe-inline'",
		"connect-src 'self' https://pds-portail-backend.fly.dev https://opendata.swiss",
		"img-src 'self' https://opendata.swiss data:",
		"font-src 'self'",
		"frame-ancestors 'none'",
		"form-action 'self'",
		"base-uri 'self'",
		"object-src 'none'"
	].join('; ');

export const handle: Handle = async ({ event, resolve }) => {
	const nonce = crypto.randomBytes(16).toString('base64url');
	event.locals.nonce = nonce;

	const response = await resolve(event);
	response.headers.set('Content-Security-Policy', buildCsp(nonce));
	return response;
};
