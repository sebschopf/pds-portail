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

<section class="stack">
	<Breadcrumb items={breadcrumbItems} ariaLabel="Fil de navigation ponderation" />
	<Card title="Comment le score de pertinence est calcule" subtitle="Score hybride combinant texte, qualite et fraicheur (PDS-40)">

		<section class="panel" aria-labelledby="ranking-formula-title">
			<h3 id="ranking-formula-title">Formule du score hybride</h3>
			<p>
				Le score de pertinence combine trois signaux ponderes, calcules pour chaque dataset lorsqu'une recherche texte est active.
			</p>
			<p class="formula">
				Score = 50% x Pertinence texte + 30% x Qualite normalisee + 20% x Fraicheur
			</p>
			<p>
				Chaque composante est comprise entre 0 (tres faible) et 1 (tres fort). Le score final est egalement entre 0 et 1, exprime en pourcentage dans l'interface.
			</p>
		</section>

		<section class="panel" aria-labelledby="ranking-text-title">
			<h3 id="ranking-text-title">Composante 1 — Pertinence texte (50%)</h3>
			<p>
				<strong>Comment c'est calcule :</strong> le moteur verifie si les mots de votre recherche apparaissent dans le titre ou la description du dataset. Chaque terme trouve contribue au score, normalise par le nombre total de termes de la requete.
			</p>
			<p>
				<strong>Comment verifier :</strong> si le titre contient les mots-clés de votre recherche, la composante texte sera elevee. Si aucun terme ne correspond, elle sera nulle.
			</p>
			<p class="note">
				Limite connue : la recherche ne gere pas encore les accents ni les variantes multilingues (ex: « mobilité » ne trouvera pas « mobilite »). Cette amelioration est prevue dans la suite de la phase 6 (PDS-41).
			</p>
		</section>

		<section class="panel" aria-labelledby="ranking-quality-title">
			<h3 id="ranking-quality-title">Composante 2 — Qualite technique (30%)</h3>
			<p>
				<strong>Comment c'est calcule :</strong> le score qualite (sur 100, voir section « Qualite » de la fiche dataset) est ramene entre 0 et 1. Un score qualite de 87 donne une composante de 0,87.
			</p>
			<p>
				<strong>Comment verifier :</strong> le score qualite est affiche dans la fiche dataset et dans la carte de resultat. Il reflete la completude des metadonnees, la presence de formats standards, les signaux geo-temporels et le nombre de ressources.
			</p>
		</section>

		<section class="panel" aria-labelledby="ranking-freshness-title">
			<h3 id="ranking-freshness-title">Composante 3 — Fraicheur des donnees (20%)</h3>
			<p>
				<strong>Comment c'est calcule :</strong> plus les donnees sont recentes, plus la composante est elevee. La formule utilise un decay exponentiel : la contribution diminue progressivement avec l'age du dataset (facteur d'echelle : 90 jours).
			</p>
			<ul>
				<li>Donnees mises a jour aujourd'hui → fraicheur = 100%</li>
				<li>Donnees mises a jour il y a 90 jours → fraicheur ≈ 37%</li>
				<li>Donnees mises a jour il y a 180 jours → fraicheur ≈ 14%</li>
				<li>Date de mise a jour inconnue → fraicheur = 0%</li>
			</ul>
			<p>
				<strong>Comment verifier :</strong> le nombre de jours depuis la derniere mise a jour est affiche dans la carte de resultat (« Fraicheur (jours) »).
			</p>
		</section>

		<section class="panel" aria-labelledby="ranking-weights-title">
			<h3 id="ranking-weights-title">Pourquoi ces poids ?</h3>
			<p>
				Les poids 50% / 30% / 20% sont un compromis documente (PDS-40) :
			</p>
			<ul>
				<li><strong>Texte (50%)</strong> : la pertinence semantique est le signal principal — un bon resultat doit parler de ce que vous cherchez.</li>
				<li><strong>Qualite (30%)</strong> : la fiabilite des metadonnees est un critere discriminant fort — des donnees mal documentees sont moins exploitables.</li>
				<li><strong>Fraicheur (20%)</strong> : la recence est importante mais pas dominante — des donnees plus anciennes mais de qualite et pertinentes peuvent rester utiles.</li>
			</ul>
			<p class="note">
				Ces poids sont versionnes et pourront evoluer avec les retours utilisateurs (phase 7).
			</p>
		</section>

		<section class="panel limits" aria-labelledby="ranking-limits-title">
			<h3 id="ranking-limits-title">Limites d'interpretation</h3>
			<ul>
				<li>Le score hybride ne s'applique que lorsqu'une recherche texte est active. Sans recherche, le tri par defaut est par date de modification.</li>
				<li>Le score textuel ne gere pas les accents ni les synonymes (ameliore en phase 6, PDS-41).</li>
				<li>Le score qualite est base sur les metadonnees publiees — il ne garantit pas que les donnees sont vraies ou completes dans le monde reel.</li>
				<li>La fraicheur depend de la date de derniere modification declaree par l'organisation productrice.</li>
				<li>Les poids sont statiques pour le MVP ; ils pourront etre ajustes via les KPI d'usage (phase 7, PDS-47).</li>
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