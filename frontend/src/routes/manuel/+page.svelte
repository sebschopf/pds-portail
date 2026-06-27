<script lang="ts">
	import { fade } from 'svelte/transition';
</script>

<svelte:head>
	<title>Manuel d’utilisation — PDS Portail</title>
</svelte:head>

<article class="manuel" in:fade={{ duration: 200 }}>
	<h2>Manuel d’utilisation</h2>
	<p class="intro">
		Bienvenue sur PDS Portail, l’explorateur Open Data Suisse. Ce manuel vous guide pas à pas
		pour rechercher, comprendre et comparer des jeux de données publics issus d’opendata.swiss.
	</p>

	<section aria-labelledby="rechercher">
		<h3 id="rechercher">🔍 Rechercher des datasets</h3>
		<p>
			Sur la page d’accueil, utilisez la <strong>barre de recherche</strong> pour saisir
			un ou plusieurs mots-clés (exemple : « population suisse », « transports publics »).
			L’application comprend le français, l’allemand et l’anglais.
		</p>
		<p>
			Les résultats s’affichent sous forme de <strong>cartes</strong>. Chaque carte montre
			le titre, l’organisation productrice, le score de qualité et la date de mise à jour.
			Vous pouvez <strong>trier</strong> les résultats par pertinence (par défaut) ou par
			qualité.
		</p>
	</section>

	<section aria-labelledby="comprendre">
		<h3 id="comprendre">📊 Comprendre un dataset</h3>
		<p>
			Cliquez sur un résultat pour ouvrir la <strong>fiche dataset</strong>. Vous y trouverez :
		</p>
		<ul>
			<li><strong>Métadonnées</strong> : description, catégories, mots-clés, licence</li>
			<li><strong>Score de qualité</strong> : évalué sur la complétude, la fraîcheur et
			l’accessibilité des métadonnées</li>
			<li><strong>Graphique radar</strong> : visualisation des forces et faiblesses du dataset</li>
			<li><strong>Ressources</strong> : liste des fichiers disponibles (CSV, JSON, PDF, etc.)
			avec leur taille et leur format</li>
		</ul>
	</section>

	<section aria-labelledby="personnaliser">
		<h3 id="personnaliser">⚖️ Personnaliser les critères de qualité</h3>
		<p>
			Chaque dataset a un score de qualité calculé automatiquement. Si vous avez des priorités
			spécifiques, vous pouvez <strong>ajuster la pondération</strong> des critères :
		</p>
		<ol>
			<li>Sur la fiche d’un dataset, cliquez sur <strong>« Personnaliser la pondération »</strong></li>
			<li>Attribuez un poids (0 à 100) à chaque critère : complétude, fraîcheur, accessibilité</li>
			<li>Le score est recalculé immédiatement selon vos préférences</li>
		</ol>
		<p>Cette pondération est conservée pendant votre session et s’applique à tous les datasets.</p>
	</section>

	<section aria-labelledby="comparer">
		<h3 id="comparer">🆚 Comparer des datasets</h3>
		<p>
			Pour comparer jusqu’à <strong>4 datasets</strong> côte à côte :
		</p>
		<ol>
			<li>Sur la page d’accueil, cochez les datasets qui vous intéressent</li>
			<li>Une <strong>barre de comparaison</strong> apparaît en bas de l’écran</li>
			<li>Cliquez sur <strong>« Comparer »</strong> pour ouvrir le tableau comparatif</li>
		</ol>
		<p>
			Le comparateur affiche côte à côte : titre, organisation, score de qualité,
			nombre de ressources, licence et date de mise à jour. Les colonnes sont
			défilables horizontalement sur mobile.
		</p>
	</section>

	<section aria-labelledby="ressources">
		<h3 id="ressources">📁 Explorer les ressources</h3>
		<p>
			Chaque dataset contient une ou plusieurs <strong>ressources</strong> (fichiers de données).
			Sur la fiche ressource, vous pouvez :
		</p>
		<ul>
			<li>Consulter le <strong>format</strong> et la <strong>taille</strong> du fichier</li>
			<li>Accéder au <strong>téléchargement direct</strong> (URL)</li>
			<li>Obtenir le <strong>lien API CKAN</strong> pour une utilisation programmatique</li>
		</ul>
	</section>

	<section aria-labelledby="accessibilite">
		<h3 id="accessibilite">♿ Accessibilité</h3>
		<p>
			PDS Portail respecte les normes <strong>WCAG 2.2 Niveau AA</strong>. Voici les
			fonctionnalités disponibles :
		</p>
		<ul>
			<li><strong>Navigation clavier</strong> : toutes les actions sont accessibles sans souris</li>
			<li><strong>Skip-link</strong> : lien « Aller au contenu principal » au début de chaque page</li>
			<li><strong>Mode lecture</strong> : activez-le via le bouton en haut de page pour
			augmenter la taille du texte et l’interligne</li>
			<li><strong>Contrastes</strong> : ratio minimum de 4.5:1 pour tous les textes</li>
			<li><strong>Respect du mouvement réduit</strong> : si votre système utilise
			<code>prefers-reduced-motion</code>, les animations sont désactivées</li>
		</ul>
	</section>

	<nav class="manuel-back" aria-label="Retour">
		<a href="/">← Retour à l’accueil</a>
	</nav>
</article>

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
		font-size: var(--font-size-heading-sm);
		color: var(--color-on-surface-muted);
		margin-bottom: var(--space-6);
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
