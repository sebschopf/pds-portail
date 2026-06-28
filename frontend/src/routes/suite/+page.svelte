<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	import { DatasetIcon, ExternalLinkIcon, Timeline } from '$lib';
	import type { ComponentProps } from 'svelte';

	const steps: ComponentProps<typeof Timeline>['steps'] = [
		{ date: '2024-2026', label: 'MVP livré et déployé', detail: 'Recherche, qualité, comparaison, accessibilité WCAG AA', state: 'done' },
		{ date: 'Été 2026', label: 'Préparation multisource', detail: 'Schéma prêt pour metadata.swiss, protocole de veille activé', state: 'current' },
		{ date: '2027', label: 'Veille et améliorations', detail: 'Surveillance des APIs, améliorations UX continues', state: 'upcoming' },
		{ date: '2028', label: 'Migration vers metadata.swiss', detail: 'Bascule vers la nouvelle plateforme unifiée DCAT-AP', state: 'upcoming' }
	];
</script>

<svelte:head>
	<title>Suite du projet — PDS Portail</title>
	<meta name="description" content="Découvrez l'évolution prévue de PDS Portail face à la transition d'opendata.swiss vers metadata.swiss." />
</svelte:head>

<article class="suite" in:fade={{ duration: 200 }}>
	<h2>Suite du projet</h2>

	<p class="intro">
		PDS Portail est un projet vivant. Il évolue avec les données publiques suisses.
		Voici où nous en sommes et ce qui se prépare.
	</p>

	<!-- Section 1 : Aujourd'hui -->
	<section aria-labelledby="aujourdhui" in:fly={{ y: 12, duration: 300 }}>
		<h3 id="aujourdhui">
			<DatasetIcon size="1.5em" label="" />
			Aujourd'hui : les données d'opendata.swiss
		</h3>
		<p>
			PDS Portail puise ses données dans le catalogue
			<a
				href="https://opendata.swiss"
				target="_blank"
				rel="noopener noreferrer"
				aria-label="opendata.swiss (s'ouvre dans une nouvelle fenêtre)"
			>opendata.swiss</a>,
			la plateforme officielle d'Open Government Data de la Confédération suisse.
		</p>
		<p>
			Ce catalogue contient <strong>plusieurs milliers de jeux de données</strong>
			publiés par les administrations fédérales, cantonales et communales&nbsp;:
			statistiques, cartes, rapports, données environnementales, transports,
			santé, et bien d'autres thèmes.
		</p>
		<p>
			La technologie sous-jacente s'appelle <strong>CKAN</strong> (Comprehensive
			Knowledge Archive Network), un standard international de catalogage de
			données ouvertes. PDS Portail interroge cette API pour vous présenter
			les données de manière lisible et accessible.
		</p>
	</section>

	<!-- Section 2 : La transition -->
	<section aria-labelledby="transition" in:fly={{ y: 12, duration: 300 }}>
		<h3 id="transition">
			<ExternalLinkIcon size="1.5em" label="" />
			Ce qui change : vers metadata.swiss
		</h3>
		<p>
			La Confédération suisse prépare une <strong>nouvelle plateforme</strong>
			pour ses métadonnées publiques. Elle s'appellera
			<strong>metadata.swiss</strong> et remplacera à terme opendata.swiss.
			L'horizon annoncé est <strong>2028</strong>.
		</p>
		<p>
			Cette nouvelle plateforme s'appuiera sur le standard
			<a
				href="https://www.dcat-ap.ch/"
				target="_blank"
				rel="noopener noreferrer"
				aria-label="DCAT-AP Suisse (s'ouvre dans une nouvelle fenêtre)"
			>DCAT-AP Suisse<ExternalLinkIcon size="0.85em" label="" /></a>,
			une norme européenne de description des données publiques.
			L'objectif&nbsp;:
			des métadonnées plus riches, mieux structurées, et multilingues
			(français, allemand, italien, anglais).
		</p>
		<p>
			En parallèle, la plateforme d'interopérabilité
			<a
				href="https://i14y-ch.github.io/handbook/fr/"
				target="_blank"
				rel="noopener noreferrer"
				aria-label="Handbook I14Y (s'ouvre dans une nouvelle fenêtre)"
			>I14Y<ExternalLinkIcon size="0.85em" label="" /></a>
			(plateforme suisse d'échange de métadonnées) enrichit déjà le paysage
			avec des <strong>concepts sémantiques</strong>, des
			<strong>services de données</strong> et des
			<strong>prestations publiques</strong> documentés. I14Y et opendata.swiss
			convergeront dans metadata.swiss.
		</p>
	</section>

	<!-- Section 3 : Ce que fait PDS Portail -->
	<section aria-labelledby="actions" in:fly={{ y: 12, duration: 300 }}>
		<h3 id="actions">
			<DatasetIcon size="1.5em" label="" />
			Ce que fait PDS Portail
		</h3>
		<p>
			Nous suivons cette transition de près. Voici nos actions concrètes&nbsp;:
		</p>
		<ul>
			<li>
				<strong>Veille active</strong>, nous surveillons les évolutions
				des APIs I14Y et les annonces concernant metadata.swiss pour ne rien manquer.
			</li>
			<li>
				<strong>Préparation technique</strong>, notre base de données est
				déjà prête à accueillir plusieurs sources de données, pour une
				transition en douceur le moment venu.
			</li>
			<li>
				<strong>Transparence</strong>, nous documentons publiquement
				nos décisions et notre stratégie. Cette page en fait partie.
			</li>
			<li>
				<strong>Continuité de service</strong>, pendant toute la transition,
				PDS Portail continue de fonctionner normalement. L'accès aux données
				ne sera pas interrompu.
			</li>
		</ul>
	</section>

	<!-- Section 4 : Calendrier -->
	<section aria-labelledby="calendrier" in:fly={{ y: 12, duration: 300 }}>
		<h3 id="calendrier">
			<ExternalLinkIcon size="1.5em" label="" />
			Calendrier prévisionnel
		</h3>

		<Timeline {steps} ariaLabel="Chronologie du projet PDS-Portail" />
	</section>

	<!-- Section 5 : Ressources -->
	<section aria-labelledby="ressources" in:fly={{ y: 12, duration: 300 }}>
		<h3 id="ressources">
			<ExternalLinkIcon size="1.5em" label="" />
			Ressources officielles
		</h3>
		<ul class="resources-list">
			<li>
				<a
					href="https://opendata.swiss/fr/"
					target="_blank"
					rel="noopener noreferrer"
					aria-label="opendata.swiss — Catalogue Open Data Suisse (s'ouvre dans une nouvelle fenêtre)"
				>
					opendata.swiss — Catalogue Open Data Suisse
					<ExternalLinkIcon size="0.9em" label="" />
				</a>
				<span class="resource-desc">La plateforme actuelle, propulsée par CKAN</span>
			</li>
			<li>
				<a
					href="https://i14y-ch.github.io/handbook/fr/"
					target="_blank"
					rel="noopener noreferrer"
					aria-label="Handbook I14Y — Plateforme d'interopérabilité (s'ouvre dans une nouvelle fenêtre)"
				>
					Handbook I14Y — Plateforme d'interopérabilité
					<ExternalLinkIcon size="0.9em" label="" />
				</a>
				<span class="resource-desc">Documentation officielle de l'API I14Y</span>
			</li>
			<li>
				<a
					href="https://www.dcat-ap.ch/"
					target="_blank"
					rel="noopener noreferrer"
					aria-label="DCAT-AP Suisse — Standard de métadonnées (s'ouvre dans une nouvelle fenêtre)"
				>
					DCAT-AP Suisse — Standard de métadonnées
					<ExternalLinkIcon size="0.9em" label="" />
				</a>
				<span class="resource-desc">La norme que metadata.swiss adoptera</span>
			</li>
			<li>
				<a
					href="https://github.com/I14Y-ch"
					target="_blank"
					rel="noopener noreferrer"
					aria-label="GitHub I14Y-ch — Code source (s'ouvre dans une nouvelle fenêtre)"
				>
					GitHub I14Y-ch — Code source
					<ExternalLinkIcon size="0.9em" label="" />
				</a>
				<span class="resource-desc">Développement open-source (dès fin 2026)</span>
			</li>
		</ul>
	</section>

	<nav class="suite-back" aria-label="Retour">
		<a href="/">← Retour à l'accueil</a>
	</nav>
</article>

<style>
	.suite {
		max-width: 68ch;
	}

	.suite h2 {
		font-family: var(--font-display);
		font-size: var(--font-size-heading-xl);
		line-height: var(--line-height-title);
		margin: 0 0 var(--space-4);
	}

	.intro {
		font-size: var(--font-size-body);
		color: var(--color-on-surface-muted);
		margin-bottom: var(--space-6);
		max-width: 60ch;
	}

	section {
		margin-bottom: var(--space-5);
		padding-left: var(--space-4);
		border-left: var(--border-strong) solid var(--color-primary);
	}

	section h3 {
		margin: 0 0 var(--space-2);
		font-size: var(--font-size-heading-sm);
		font-family: var(--font-display);
		line-height: var(--line-height-title);
		display: flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-primary);
	}

	section p,
	section li {
		font-size: var(--font-size-body);
		line-height: var(--line-height-body);
		color: var(--color-on-surface);
	}

	section ul {
		margin: var(--space-2) 0;
		padding-left: var(--space-5);
	}

	section li {
		margin-bottom: var(--space-1);
	}

	/* ── Ressources ─────────────────────── */

	.resources-list {
		list-style: none;
		padding-left: 0;
		margin: var(--space-2) 0;
	}

	.resources-list li {
		margin-bottom: var(--space-3);
		display: flex;
		flex-direction: column;
		gap: var(--space-0);
	}

	.resources-list a {
		font-weight: 650;
		color: var(--color-primary);
		text-decoration-thickness: 2px;
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
	}

	.resources-list a:hover {
		color: var(--color-on-surface);
	}

	.resource-desc {
		font-size: var(--font-size-caption);
		color: var(--color-on-surface-subtle);
	}

	/* ── Retour ──────────────────────────── */

	.suite-back {
		margin-top: var(--space-6);
		padding-top: var(--space-4);
		border-top: var(--border-thin) solid var(--color-border);
	}

	.suite-back a {
		font-weight: 650;
		color: var(--color-primary);
		text-decoration-thickness: 2px;
	}

	.suite-back a:hover {
		color: var(--color-on-surface);
	}
</style>