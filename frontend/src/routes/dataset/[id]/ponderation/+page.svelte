<script lang="ts">
	import { Breadcrumb, Card } from '$lib';

	let { data } = $props();

	const datasetLink = $derived(`/dataset/${encodeURIComponent(data.datasetId)}`);
	const breadcrumbItems = $derived([
		{ label: 'Recherche', href: '/' },
		{ label: 'Fiche dataset', href: datasetLink },
		{ label: 'Ponderation du score' }
	]);
</script>

<section class="stack">
	<Breadcrumb items={breadcrumbItems} ariaLabel="Fil de navigation ponderation" />
	<Card title="Ponderation du score qualite" subtitle="Explication des 5 composantes et methode de verification">
		<section class="panel" aria-labelledby="ponderation-formula-title">
			<h3 id="ponderation-formula-title">Formule du score</h3>
			<p>
				Le score qualite est un indicateur sur 100. Il combine 5 composantes a poids egal:
				completude, fraicheur, formats standards, signal geo-temporel et nombre de ressources.
			</p>
			<p class="formula">
				Score = 20 x (Completude + Fraicheur + Formats standards + Signal geo-temporel + Nombre de
				ressources)
			</p>
			<p>
				Chaque composante vaut 0, 0.5 ou 1 selon les informations disponibles.
			</p>
		</section>

		<section class="panel" aria-labelledby="ponderation-completeness-title">
			<h3 id="ponderation-completeness-title">Composante 1 - Completude</h3>
			<p>
				<strong>Comment c est calcule:</strong> la note est calculee sur 5 verifications: description
				renseignee, tags presents, date de creation, date de modification et au moins 1 ressource.
			</p>
			<p>
				<strong>Comment je peux verifier:</strong> dans la fiche dataset, verifier que la description est
				renseignee, que des tags sont presents, que les dates metadata existent et qu au moins une
				ressource est listee.
			</p>
		</section>

		<section class="panel" aria-labelledby="ponderation-freshness-title">
			<h3 id="ponderation-freshness-title">Composante 2 - Fraicheur</h3>
			<p><strong>Comment c est calcule:</strong> plus la derniere mise a jour est recente, plus la note est haute.</p>
			<p>
				<strong>Comment je peux verifier:</strong> comparer la date de mise a jour du dataset avec la date du
				jour et verifier le nombre de jours affiches.
			</p>
		</section>

		<section class="panel" aria-labelledby="ponderation-formats-title">
			<h3 id="ponderation-formats-title">Composante 3 - Formats standards</h3>
			<p>
				<strong>Comment c est calcule:</strong> la note est haute si au moins un format standard est present
				(CSV, JSON, GEOJSON, API).
			</p>
			<p>
				<strong>Comment je peux verifier:</strong> ouvrir la section ressources et verifier le format de chaque
				ressource.
			</p>
		</section>

		<section class="panel" aria-labelledby="ponderation-signal-title">
			<h3 id="ponderation-signal-title">Composante 4 - Signal geo-temporel</h3>
			<p>
				<strong>Comment c est calcule:</strong> la note monte si des signaux geographiques sont presents dans
				les tags et si une date de creation ou modification est renseignee.
			</p>
			<p>
				<strong>Comment je peux verifier:</strong> verifier la presence de tags geographiques et des dates
				metadata sur la fiche dataset.
			</p>
		</section>

		<section class="panel" aria-labelledby="ponderation-resources-title">
			<h3 id="ponderation-resources-title">Composante 5 - Nombre de ressources</h3>
			<p>
				<strong>Comment c est calcule:</strong> la note augmente avec le nombre de ressources associees au
				dataset.
			</p>
			<p>
				<strong>Comment je peux verifier:</strong> compter les ressources listees dans la section "Ressources
				associees".
			</p>
		</section>

		<section class="panel limits" aria-labelledby="ponderation-limits-title">
			<h3 id="ponderation-limits-title">Limites d interpretation</h3>
			<p>
				Ce score aide a comparer la qualite technique de publication. Il ne prouve pas que les donnees sont
				vraies, completes dans le monde reel ou adaptees a tous les usages.
			</p>
			<p>
				Avant reutilisation, verifier aussi la source, la periode couverte, la methode de collecte et la
				licence.
			</p>
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

	.formula {
		font-weight: 700;
		padding: var(--space-2) var(--space-3);
		background: var(--color-surface);
		border: var(--border-thin) dashed var(--color-border);
	}

	.limits {
		background: color-mix(in oklch, var(--color-warning) 18%, var(--color-surface-muted));
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