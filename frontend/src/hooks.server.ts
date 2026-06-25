import type { Handle } from '@sveltejs/kit';

const CSP_DIRECTIVES = [
	"default-src 'self'",
	"script-src 'self'",
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
	const response = await resolve(event);
	response.headers.set('Content-Security-Policy', CSP_DIRECTIVES);
	return response;
};