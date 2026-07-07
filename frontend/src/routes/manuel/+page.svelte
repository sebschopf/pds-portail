<script lang="ts">
	import { fade } from 'svelte/transition';
	import SearchIcon from '$lib/assets/icons/SearchIcon.svelte';
	import DatasetIcon from '$lib/assets/icons/DatasetIcon.svelte';
	import CompareIcon from '$lib/assets/icons/CompareIcon.svelte';
	import AccessibilityIcon from '$lib/assets/icons/AccessibilityIcon.svelte';
</script>

<svelte:head>
	<title>Manuel d'utilisation — PDS Portail</title>
</svelte:head>

<article class="manuel" in:fade={{ duration: 200 }}>
	<h2>Manuel d'utilisation</h2>
	<p class="intro">
		PDS Portail vous aide à explorer les données publiques de la Suisse.
		Pas besoin d'être expert&nbsp;: tout est conçu pour que vous trouviez,
		compreniez et compariez des jeux de données en quelques clics.
	</p>

	<section aria-labelledby="rechercher">
		<h3 id="rechercher">
			<SearchIcon size="1.5em" label="" />
			Rechercher des données
		</h3>
		<p>
			Tapez un ou deux mots dans la barre de recherche. Par exemple
			<em>«&nbsp;population suisse&nbsp;»</em> ou <em>«&nbsp;transports&nbsp;»</em>.
			L'application comprend le français, l'allemand et l'anglais.
		</p>
		<p>
			Les <strong>résultats</strong> s'affichent en cartes. Chaque carte
			vous montre d'un coup d'œil le titre, l'organisation qui publie,
			un score de qualité et la date de mise à jour. Vous pouvez trier
			par <strong>pertinence</strong> ou par <strong>qualité</strong>.
		</p>
	</section>

	<section aria-labelledby="comprendre">
		<h3 id="comprendre">
			<DatasetIcon size="1.5em" label="" />
			Comprendre un jeu de données
		</h3>
		<p>
			Cliquez sur une carte pour ouvrir la <strong>fiche détaillée</strong>.
			Vous y trouverez&nbsp;:
		</p>
		<ul>
			<li>La <strong>description</strong> du jeu de données, ses thèmes et sa licence</li>
			<li>Un <strong>score de qualité</strong> basé sur la complétude, la fraîcheur et l'accessibilité</li>
			<li>Un <strong>graphique radar</strong> pour repérer visuellement les forces et les faiblesses</li>
			<li>La <strong>liste des fichiers</strong> disponibles, avec leur format et leur taille</li>
		</ul>
	</section>

	<section aria-labelledby="surveillance">
		<h3 id="surveillance">
			<DatasetIcon size="1.5em" label="" />
			Service payant&nbsp;: Surveiller des datasets
		</h3>
		<p>
			Vous pouvez <strong>surveiller plusieurs datasets</strong> et recevoir une alerte par email
			à chaque modification détectée. Ce service coûte <strong>5 CHF par mois</strong> (abonnement
			unique, quel que soit le nombre de datasets surveillés).
		</p>

		<h4>Ce que vous obtenez</h4>
		<ul>
			<li>Un <strong>email d'alerte</strong> dès qu'un changement est détecté (métadonnées, ressources, qualité, liens)</li>
			<li>Un <strong>tableau de bord personnel</strong> avec l'historique complet des changements</li>
			<li>La possibilité d'arrêter la surveillance à tout moment</li>
		</ul>

		<h4>Comment ça marche</h4>
		<ol>
			<li>Sur une fiche dataset, cliquez sur <strong>«&nbsp;Surveiller ce dataset&nbsp;»</strong></li>
			<li>Entrez votre adresse email et cliquez sur <strong>«&nbsp;Procéder au paiement&nbsp;»</strong></li>
			<li>Vous êtes redirigé vers <strong>Polar</strong> pour finaliser le paiement (carte bancaire)</li>
			<li>Une fois le paiement confirmé, vous recevez un <strong>email de bienvenue</strong> contenant un lien vers votre tableau de bord</li>
			<li>Cliquez sur <strong>«&nbsp;Accéder à mon tableau de bord&nbsp;»</strong> dans l'email pour voir vos datasets surveillés et l'historique des alertes</li>
		</ol>

		<h4>Accéder à votre tableau de bord</h4>
		<p>
			Votre tableau de bord est accessible à tout moment depuis la page
			<a href="/alertes"><strong>Mes alertes</strong></a>.
			Deux méthodes pour vous connecter&nbsp;:
		</p>
		<ul>
			<li><strong>Navigateur reconnu</strong>&nbsp;: si vous avez déjà ouvert le tableau de bord sur ce navigateur, vous êtes reconnecté automatiquement</li>
			<li><strong>Lien email</strong>&nbsp;: demandez un lien d'accès temporaire (valable 15 minutes) en entrant votre email sur la page Mes alertes</li>
		</ul>
		<p>
			PDS-Portail ne stocke jamais vos données bancaires. Le paiement est géré par Polar.
		</p>
	</section>

	<section aria-labelledby="comparer">
		<h3 id="comparer">
			<CompareIcon size="1.5em" label="" />
			Comparer jusqu'à 4 jeux de données
		</h3>
		<p>
			Vous hésitez entre plusieurs datasets&nbsp;? Comparez-les côte à côte&nbsp;:
		</p>
		<ol>
			<li>Sur la page d'accueil, <strong>cochez les cases</strong> des datasets qui vous intéressent</li>
			<li>Une barre apparaît en bas de l'écran avec les datasets sélectionnés</li>
			<li>Cliquez sur <strong>«&nbsp;Comparer&nbsp;»</strong> pour voir le tableau comparatif</li>
		</ol>
		<p>
			Le comparateur affiche le titre, l'organisation, le score de qualité,
			le nombre de ressources, la licence et la date de mise à jour.
			Sur mobile, faites glisser le tableau horizontalement.
		</p>
	</section>

	<section aria-labelledby="ressources">
		<h3 id="ressources">
			<DatasetIcon size="1.5em" label="" />
			Explorer les fichiers de données
		</h3>
		<p>
			Chaque dataset contient un ou plusieurs <strong>fichiers</strong>.
			Sur la fiche ressource, vous pouvez&nbsp;:
		</p>
		<ul>
			<li>Voir le <strong>format</strong> et la <strong>taille</strong> du fichier</li>
			<li>Télécharger le fichier directement via son URL</li>
			<li>Récupérer le <strong>lien API</strong> si vous voulez utiliser les données dans un programme</li>
		</ul>
	</section>


<style>
	.manuel {
		max-width: 68ch;
	}

	.manuel h2 {
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

	section ul,
	section ol {
		margin: var(--space-2) 0;
		padding-left: var(--space-5);
	}

	section li {
		margin-bottom: var(--space-1);
	}

	.manuel-back {
		margin-top: var(--space-6);
		padding-top: var(--space-4);
		border-top: var(--border-thin) solid var(--color-border);
	}

	.manuel-back a {
		font-weight: 650;
		color: var(--color-primary);
		text-decoration-thickness: 2px;
	}

	.manuel-back a:hover {
		color: var(--color-on-surface);
	}
</style>

	<section aria-labelledby="accessibilite">
		<h3 id="accessibilite">
			<AccessibilityIcon size="1.5em" label="" />
			Accessibilité
		</h3>
		<p>
			PDS Portail respecte la norme <strong>WCAG 2.2 Niveau AA</strong>.
			Concrètement, ça veut dire&nbsp;:
		</p>
		<ul>
			<li><strong>Tout est utilisable au clavier</strong>, sans souris</li>
			<li>Un lien <strong>«&nbsp;Aller au contenu principal&nbsp;»</strong> en haut de chaque page</li>
			<li>Un <strong>bouton Mode lecture</strong> dans l'en-tête pour agrandir le texte et l'interligne</li>
			<li>Des <strong>contrastes élevés</strong> pour une lecture confortable</li>
			<li>Si votre système préfère <strong>moins d'animations</strong>, elles sont automatiquement réduites</li>
		</ul>
	</section>

	<nav class="manuel-back" aria-label="Retour">
		<a href="/">← Retour à l'accueil</a>
	</nav>
</article>
