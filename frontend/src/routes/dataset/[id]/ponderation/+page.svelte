<script lang="ts">
	import { Breadcrumb, Card } from '$lib';

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

<section class="stack">
	<Breadcrumb items={breadcrumbItems} ariaLabel="Fil de navigation ponderation" />
	<Card title="Comment le score de pertinence est calcule" subtitle="Les trois criteres qui determinent l'ordre des resultats">

		<section class="panel" aria-labelledby="ranking-formula-title">
			<h3 id="ranking-formula-title">Formule du score</h3>
			<p>
				Lorsque vous faites une recherche texte, chaque dataset recoit un score de pertinence qui combine trois criteres. Ce score determine sa position dans la liste des resultats.
			</p>
			<p class="formula">
				Score = 50% x Pertinence du texte + 30% x Qualite des donnees + 20% x Fraicheur
			</p>
			<p>
				Le score final est toujours compris entre 0% et 100%. Il est affiche en pourcentage dans chaque carte de resultat.
			</p>
		</section>

		<section class="panel" aria-labelledby="ranking-text-title">
			<h3 id="ranking-text-title">Critere 1: Pertinence du texte (50%)</h3>
			<p>
				<strong>Comment c'est calcule:</strong> nous verifions si les mots de votre recherche apparaissent dans le titre ou la description du jeu de donnees. Plus il y a de correspondances, plus ce critere est eleve.
			</p>
			<p>
				<strong>Comment verifier:</strong> si le titre contient les mots-cles de votre recherche, ce critere sera eleve. Si aucun terme ne correspond, il sera nul.
			</p>
			<p class="note">
				Limite actuelle: la recherche ne tient pas encore compte des accents ni des variantes de langue (par exemple « mobilite » ne trouvera pas « mobilité »). Cette amelioration est prevue prochainement.
			</p>
		</section>

		<section class="panel" aria-labelledby="ranking-quality-title">
			<h3 id="ranking-quality-title">Critere 2: Qualite des donnees (30%)</h3>
			<p>
				<strong>Comment c'est calcule:</strong> le score de qualite (sur 100, visible dans la section « Qualite » de la fiche dataset) est ramene sur une echelle de 0 a 1. Par exemple, un score qualite de 87 donne un critere de 0,87.
			</p>
			<p>
				<strong>Comment verifier:</strong> le score de qualite est affiche dans la fiche dataset et dans chaque carte de resultat. Il reflete la completude des informations, la presence de formats standard, les indications geographiques et temporelles, ainsi que le nombre de ressources disponibles.
			</p>
		</section>

		<section class="panel" aria-labelledby="ranking-freshness-title">
			<h3 id="ranking-freshness-title">Critere 3: Fraicheur des donnees (20%)</h3>
			<p>
				<strong>Comment c'est calcule:</strong> plus les donnees sont recentes, plus ce critere est eleve. La contribution diminue progressivement avec l'age du jeu de donnees. L'echelle de reference est de 90 jours.
			</p>
			<ul>
				<li>Donnees mises a jour aujourd'hui: fraicheur = 100%</li>
				<li>Donnees mises a jour il y a 90 jours: fraicheur ≈ 37%</li>
				<li>Donnees mises a jour il y a 180 jours: fraicheur ≈ 14%</li>
				<li>Date de mise a jour inconnue: fraicheur = 0%</li>
			</ul>
			<p>
				<strong>Comment verifier:</strong> le nombre de jours depuis la derniere mise a jour est affiche dans la carte de resultat (indication « Fraicheur (jours) »).
			</p>
		</section>

		<section class="panel" aria-labelledby="ranking-weights-title">
			<h3 id="ranking-weights-title">Pourquoi ces pourcentages ?</h3>
			<p>
				Les poids 50%, 30% et 20% refletent nos priorites pour vous aider a trouver les donnees les plus utiles:
			</p>
			<ul>
				<li><strong>Texte (50%)</strong>: c'est le critere principal. Un bon resultat doit correspondre a ce que vous cherchez.</li>
				<li><strong>Qualite (30%)</strong>: des donnees bien documentees sont plus faciles a comprendre et a reutiliser.</li>
				<li><strong>Fraicheur (20%)</strong>: des donnees recentes sont souvent plus pertinentes, mais des donnees plus anciennes et de qualite peuvent rester utiles.</li>
			</ul>
			<p class="note">
				Ces pourcentages sont fixes pour le moment. Ils pourront evoluer en fonction des retours des utilisateurs et utilisatrices.
			</p>
		</section>

		<section class="panel limits" aria-labelledby="ranking-limits-title">
			<h3 id="ranking-limits-title">Limites d'interpretation</h3>
			<ul>
				<li>Le score de pertinence ne s'applique que lorsque vous faites une recherche avec des mots-cles. Sans recherche, les resultats sont tries par date de modification.</li>
				<li>La recherche ne tient pas encore compte des accents ni des synonymes (cette amelioration est prevue prochainement).</li>
				<li>Le score de qualite est base sur les informations publiees par les organisations. Il ne garantit pas que les donnees sont exactes ou completes dans la realite.</li>
				<li>La fraicheur depend de la date de derniere modification declaree par l'organisation qui produit les donnees.</li>
				<li>Avant de reutiliser des donnees, verifiez aussi leur source, la periode couverte, la methode de collecte et la licence.</li>
			</ul>
		</section>

		<nav class="links" aria-label="Navigation ponderation">
			<a href={datasetLink}>Retour a la fiche dataset</a>
			<a href="/">Retour a la recherche</a>
		</nav>
	</Card>
</section>

<style>
	.stack {
		display: grid;
		gap: var(--space-4);
	}

	.panel {
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