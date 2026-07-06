import { env } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';
import { redirect } from '@sveltejs/kit';

type SupportWatcherSummary = {
	watcher_id: string;
	watcher_status: string;
	subscription_id_present: boolean;
	watched_datasets_count: number;
	last_webhook_at: string | null;
	last_magic_link_at: string | null;
};

type SupportSubscriptionSummary = {
	watcher_id: string;
	subscription_state: string;
	subscription_id_masked: string | null;
	updated_at: string;
};

type SupportWebhookItem = {
	event_type: string;
	received_at: string;
	delivery_status: string;
	correlation_id: string | null;
};

type SupportMagicLinkState = {
	watcher_id: string;
	last_issued_at: string | null;
	last_used_at: string | null;
	active_unexpired_count: number;
	expired_unconsumed_count: number;
};

type SupportDeliverability = {
	watcher_id: string;
	last_send_status: string | null;
	last_send_at: string | null;
	provider_message_id_masked: string | null;
	recent_error_code: string | null;
	recent_error_count_24h: number;
};

type SupportDiagnostics = {
	watcher: SupportWatcherSummary;
	subscription: SupportSubscriptionSummary;
	webhooks: SupportWebhookItem[];
	magicLinks: SupportMagicLinkState;
	deliverability: SupportDeliverability;
};

type SupportPageData = {
	status: 'idle' | 'loaded' | 'not-found' | 'error' | 'not-configured';
	email: string;
	notice: string | null;
	errorMessage: string | null;
	diagnostics: SupportDiagnostics | null;
};

const DEFAULT_BACKEND_BASE_URL = 'http://127.0.0.1:8000';

function getBackendBaseUrl(): string {
	return publicEnv.PUBLIC_API_BASE_URL || DEFAULT_BACKEND_BASE_URL;
}

function getInternalApiToken(): string | undefined {
	return process.env.INTERNAL_API_TOKEN ?? env.INTERNAL_API_TOKEN;
}

function getInternalHeaders(requestId: string): HeadersInit {
	const internalApiToken = getInternalApiToken();
	if (!internalApiToken) {
		return {};
	}

	return {
		Authorization: `Bearer ${internalApiToken}`,
		'X-Operator-Id': 'support-portal',
		'X-Request-Id': requestId
	};
}

async function readJson<T>(response: Response): Promise<T> {
	return (await response.json()) as T;
}

async function loadDiagnostics(fetchFn: typeof fetch, email: string): Promise<SupportDiagnostics> {
	const backendBaseUrl = getBackendBaseUrl();
	const requestId = crypto.randomUUID();
	const headers = getInternalHeaders(requestId);
	if (!getInternalApiToken()) {
		throw new Error('INTERNAL_API_TOKEN not configured');
	}

	const lookupResponse = await fetchFn(
		`${backendBaseUrl}/api/v1/internal/support/watchers/by-email?email=${encodeURIComponent(email)}`,
		{ headers }
	);

	if (!lookupResponse.ok) {
		throw new Error(lookupResponse.status === 404 ? 'not-found' : 'lookup-failed');
	}

	const watcher = await readJson<SupportWatcherSummary>(lookupResponse);
	const [subscriptionResponse, webhooksResponse, magicResponse, deliverabilityResponse] =
		await Promise.all([
			fetchFn(`${backendBaseUrl}/api/v1/internal/support/watchers/${watcher.watcher_id}/subscription`, {
				headers
			}),
			fetchFn(
				`${backendBaseUrl}/api/v1/internal/support/watchers/${watcher.watcher_id}/webhooks/latest?limit=5`,
				{
					headers
				}
			),
			fetchFn(
				`${backendBaseUrl}/api/v1/internal/support/watchers/${watcher.watcher_id}/magic-links/state`,
				{ headers }
			),
			fetchFn(
				`${backendBaseUrl}/api/v1/internal/support/watchers/${watcher.watcher_id}/email-deliverability`,
				{ headers }
			)
		]);

	if (!subscriptionResponse.ok || !webhooksResponse.ok || !magicResponse.ok || !deliverabilityResponse.ok) {
		throw new Error('detail-failed');
	}

	return {
		watcher,
		subscription: await readJson<SupportSubscriptionSummary>(subscriptionResponse),
		webhooks: (await readJson<{ items: SupportWebhookItem[] }>(webhooksResponse)).items,
		magicLinks: await readJson<SupportMagicLinkState>(magicResponse),
		deliverability: await readJson<SupportDeliverability>(deliverabilityResponse)
	};
}

export const load = async ({ url, fetch }: { url: URL; fetch: typeof globalThis.fetch }) => {
	const email = (url.searchParams.get('email') ?? '').trim();
	const notice = url.searchParams.get('notice');

	if (!email) {
		return {
			status: 'idle',
			email: '',
			notice,
			errorMessage: null,
			diagnostics: null
		};
	}

	if (!getInternalApiToken()) {
		return {
			status: 'not-configured',
			email,
			notice,
			errorMessage: 'Le token interne support n\'est pas configuré côté serveur.',
			diagnostics: null
		};
	}

	try {
		const diagnostics = await loadDiagnostics(fetch, email);
		return {
			status: 'loaded',
			email,
			notice,
			errorMessage: null,
			diagnostics
		};
	} catch (error) {
		const message = error instanceof Error && error.message === 'not-found'
			? 'Aucun watcher ne correspond à cette adresse email.'
			: 'Impossible de charger le diagnostic support.';
		return {
			status: error instanceof Error && error.message === 'not-found' ? 'not-found' : 'error',
			email,
			notice,
			errorMessage: message,
			diagnostics: null
		};
	}
};

export const actions = {
	resend: async ({ request, fetch }: { request: Request; fetch: typeof globalThis.fetch }) => {
		if (!getInternalApiToken()) {
			throw redirect(303, '/support?notice=not-configured');
		}

		const formData = await request.formData();
		const email = String(formData.get('email') ?? '').trim();
		const watcherId = String(formData.get('watcher_id') ?? '').trim();
		if (!email || !watcherId) {
			throw redirect(303, '/support?notice=missing-data');
		}

		const backendBaseUrl = getBackendBaseUrl();
		const requestId = crypto.randomUUID();
		const response = await fetch(
			`${backendBaseUrl}/api/v1/internal/support/watchers/${watcherId}/magic-link/resend`,
			{
				method: 'POST',
				headers: {
					...getInternalHeaders(requestId),
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ reason: 'incident_paid_no_access' })
			}
		);

		if (response.ok) {
			throw redirect(303, `/support?email=${encodeURIComponent(email)}&notice=resent`);
		}

		if (response.status === 409) {
			throw redirect(303, `/support?email=${encodeURIComponent(email)}&notice=suspended`);
		}
		if (response.status === 429) {
			throw redirect(303, `/support?email=${encodeURIComponent(email)}&notice=rate-limited`);
		}

		throw redirect(303, `/support?email=${encodeURIComponent(email)}&notice=error`);
	}
};

