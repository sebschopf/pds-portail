// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		interface Error {
			message: string;
		}
		interface Locals {
			// Réservé pour les données injectées par hooks.server.ts
		}
		// Chaque page type localement via PageLoad<MonType> ; les layouts
		// qui accèdent à data.xxx bénéficient de l'autocomplétion sur l'union
		// des types exportés par les pages filles.
		// eslint-disable-next-line @typescript-eslint/no-empty-object-type
		interface PageData {
		}
		interface Platform {
			// Plateforme de déploiement (ex: Cloudflare Workers, Deno)
		}
	}
}

export {};
