<script lang="ts">
	import { Breadcrumb, Card, PageLayout } from '$lib';

	let { data } = $props();

	const datasetLink = $derived(`/dataset/${encodeURIComponent(data.datasetId)}`);
	const breadcrumbItems = $derived([
		{ label: 'Recherche', href: '/' },
		{ label: 'Fiche dataset', href: datasetLink },
		{ label: 'Calcul du score de pertinence' }
	]);
</script>

<svelte:head>
	<title>Pondération - PDS Portail</title>
</svelte:head>

<PageLayout>
	<Breadcrumb items={breadcrumbItems} ariaLabel="Fil de navigation pondération" />
	<Card title="Comment le score de pertinence est calculé" subtitle="Les trois critères qui déterminent l'ordre des résultats">

		<section class="panel" aria-labelledby="ranking-formula-title">
			<h3 id="ranking-formula-title">Formule du score</h3>
			<p>
				Lorsque vous faites une recherche texte, chaque dataset reçoit un score de pertinence qui combine trois critères. Ce score détermine sa position dans la liste des résultats.
			</p>
			<p class="formula">
				Score = 50% x Pertinence du texte + 30% x Qualité des données + 20% x Fraîcheur
			</p>
			<p>
				Le score final est toujours compris entre 0% et 100%. Il est affiché en pourcentage dans chaque carte de résultat.
			</p>
		</section>

		<section class="panel" aria-labelledby="ranking-text-title">
			<h3 id="ranking-text-title">Critère 1: Pertinence du texte (50%)</h3>
			<p>
				<strong>Comment c'est calculé:</strong> nous vérifions si les mots de votre recherche apparaissent dans le titre ou la description du jeu de données. Plus il y a de correspondances, plus ce critère est élevé.
			</p>
			<p>
				<strong>Comment vérifier:</strong> si le titre contient les mots-clés de votre recherche, ce critère sera élevé. Si aucun terme ne correspond, il sera nul.
			</p>
			<p class="note">
				Limite actuelle: la recherche ne tient pas encore compte des accents ni des variantes de langue (par exemple « mobilité » ne trouvera pas « mobilité »). Cette amélioration est prévue prochainement.
			</p>
		</section>

		<section class="panel" aria-labelledby="ranking-quality-title">
			<h3 id="ranking-quality-title">Critère 2: Qualité des données (30%)</h3>
			<p>
				<strong>Comment c'est calculé:</strong> le score de qualité (sur 100, visible dans la section « Qualité » de la fiche dataset) est ramené sur une échelle de 0 à 1. Par exemple, un score qualité de 87 donne un critère de 0,87.
			</p>
			<p>
				<strong>Comment vérifier:</strong> le score de qualité est affiché dans la fiche dataset et dans chaque carte de résultat. Il reflète la complétude des informations, la présence de formats standard, les indications géographiques et temporelles, ainsi que le nombre de ressources disponibles.
			</p>
		</section>

		<section class="panel" aria-labelledby="ranking-freshness-title">
			<h3 id="ranking-freshness-title">Critère 3: Fraîcheur des données (20%)</h3>
			<p>
				<strong>Comment c'est calculé:</strong> plus les données sont récentes, plus ce critère est élevé. La contribution diminue progressivement avec l'âge du jeu de données. L'échelle de référence est de 90 jours.
			</p>
			<ul>
				<li>Données mises à jour aujourd'hui: fraîcheur = 100%</li>
				<li>Données mises à jour il y a 90 jours: fraîcheur ≈ 37%</li>
				<li>Données mises à jour il y a 180 jours: fraîcheur ≈ 14%</li>
				<li>Date de mise a jour inconnue: fraîcheur = 0%</li>
			</ul>
			<p>
				<strong>Comment vérifier:</strong> le nombre de jours depuis la dernière mise à jour est affiché dans la carte de résultat (indication « Fraîcheur (jours) »).
			</p>
		</section>

		<section class="panel" aria-labelledby="ranking-weights-title">
			<h3 id="ranking-weights-title">Pourquoi ces pourcentages ?</h3>
			<p>
				Les poids 50%, 30% et 20% reflètent nos priorités pour vous aider à trouver les données les plus utiles:
			</p>
			<ul>
				<li><strong>Texte (50%)</strong>: c'est le critère principal. Un bon résultat doit correspondre à ce que vous cherchez.</li>
				<li><strong>Qualité (30%)</strong>: des données bien documentées sont plus faciles à comprendre et a réutiliser.</li>
				<li><strong>Fraîcheur (20%)</strong>: des données récentes sont souvent plus pertinentes, mais des données plus anciennes et de qualité peuvent rester utiles.</li>
			</ul>
			<p class="note">
				Ces pourcentages sont fixes pour le moment. Ils pourront évoluer en fonction des retours des utilisateurs et utilisatrices.
			</p>
		</section>

		<section class="panel limits" aria-labelledby="ranking-limits-title">
			<h3 id="ranking-limits-title">Limites d'interprétation</h3>
			<ul>
				<li>Le score de pertinence ne s'applique que lorsque vous faites une recherche avec des mots-clés. Sans recherche, les résultats sont triés par date de modification.</li>
				<li>La recherche ne tient pas encore compte des accents ni des synonymes (cette amélioration est prévue prochainement).</li>
				<li>Le score de qualité est  basé sur les informations publiées par les organisations. Il ne garantit pas que les données sont exactes ou complètes dans la réalité.</li>
				<li>La fraîcheur dépend de la date de dernière modification déclarée par l'organisation qui produit les données.</li>
				<li>Avant de réutiliser des données, vérifiez aussi leur source, la période couverte, la méthode de collecte et la licence.</li>
			</ul>
		</section>

		<nav class="links" aria-label="Navigation pondération">
			<a href={datasetLink}>Retour à la fiche dataset</a>
			<a href="/">Retour à la recherche</a>
		</nav>
	</Card>
</PageLayout>

<style>	.panel {
		display: grid;
		gap: var(--space-2);
		padding: var(--space-3);
		background: var(--color-surface-muted);
		border: var(--border-thin) solid var(--color-border);
		border-radius: var(--radius-none);
	}

	h3 {
		margin: 0;
		line-height: var(--line-height-title);
		font-size: clamp(1.05rem, 0.6vw + 0.95rem, 1.25rem);
	}

	p {
		margin: 0;
		overflow-wrap: anywhere;
	}

	.panel ul {
		margin: 0;
		padding-left: var(--space-5);
		display: grid;
		gap: var(--space-1);
	}

	.formula {
		font-weight: 700;
		padding: var(--space-2) var(--space-3);
		background: var(--color-surface);
		border: var(--border-thin) dashed var(--color-border);
	}

	.note {
		font-size: var(--font-size-ui);
		color: var(--color-on-surface-muted);
		font-style: italic;
	}

	.limits {
		background: color-mix(in oklch, var(--color-warning) 18%, var(--color-surface-muted));
	}

	.limits ul {
		list-style: disc;
	}

	.links {
		display: flex;
		gap: var(--space-4);
		flex-wrap: wrap;
		margin-top: var(--space-4);
	}

	.links a {
		font-weight: 650;
		text-decoration-thickness: 2px;
		overflow-wrap: anywhere;
	}

	@media (max-width: 43.75rem) {
		.links {
			display: grid;
			gap: var(--space-3);
		}
	}
</style>