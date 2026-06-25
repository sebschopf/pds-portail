// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		interface Error {
			message: string;
		}
		interface Locals {
			nonce: string;
		}
		interface PageData {
			// Données partagées entre layouts et pages, actuellement minimales
		}
		interface Platform {
			// Plateforme de déploiement (ex: Cloudflare Workers, Deno)
		}
	}
}

export {};
