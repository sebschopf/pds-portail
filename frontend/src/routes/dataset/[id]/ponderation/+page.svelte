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
		<section class="panel" aria-label="Formule du score">
			<h3>Formule du score</h3>
			<p>
				Le score qualite est un indicateur sur 100. Il combine 5 composantes ponderees: completude,
				fraicheur, formats exploitables, couverture des ressources et structure du dataset.
			</p>
			<p class="formula" aria-label="Formule globale de ponderation">
				Score = 0.35 x Completude + 0.25 x Fraicheur + 0.15 x Formats + 0.15 x Ressources + 0.10 x
				Structure
			</p>
		</section>

		<section class="panel" aria-label="Composante completude">
			<h3>Composante 1 - Completude</h3>
			<p><strong>Comment c est calcule:</strong> la note monte quand les champs de base sont renseignes.</p>
			<p>
				<strong>Comment je peux verifier:</strong> dans la fiche dataset, verifier presence du titre, de la
				description, de l organisation et de la licence.
			</p>
		</section>

		<section class="panel" aria-label="Composante fraicheur">
			<h3>Composante 2 - Fraicheur</h3>
			<p><strong>Comment c est calcule:</strong> plus la derniere mise a jour est recente, plus la note est haute.</p>
			<p>
				<strong>Comment je peux verifier:</strong> comparer la date de mise a jour du dataset avec la date du
				jour et verifier le nombre de jours affiches.
			</p>
		</section>

		<section class="panel" aria-label="Composante formats">
			<h3>Composante 3 - Formats exploitables</h3>
			<p>
				<strong>Comment c est calcule:</strong> la note augmente quand des formats reutilisables comme CSV ou
				JSON sont disponibles.
			</p>
			<p>
				<strong>Comment je peux verifier:</strong> ouvrir la section structure ou ressources et verifier la
				presence de formats ouverts et telechargeables.
			</p>
		</section>

		<section class="panel" aria-label="Composante ressources">
			<h3>Composante 4 - Couverture des ressources</h3>
			<p>
				<strong>Comment c est calcule:</strong> la note depend du nombre de ressources publiees et de la
				presence de liens exploitables.
			</p>
			<p>
				<strong>Comment je peux verifier:</strong> dans "Ressources associees", verifier que plusieurs
				ressources sont listees et que les liens source s ouvrent.
			</p>
		</section>

		<section class="panel" aria-label="Composante structure">
			<h3>Composante 5 - Structure du dataset</h3>
			<p>
				<strong>Comment c est calcule:</strong> la note augmente quand la structure est claire, avec des champs
				identifies et une frequence de mise a jour indiquee.
			</p>
			<p>
				<strong>Comment je peux verifier:</strong> verifier les champs disponibles, les formats et la frequence
				dans le bloc "Structure du jeu de donnees".
			</p>
		</section>

		<section class="panel limits" aria-label="Limites d interpretation">
			<h3>Limites d interpretation</h3>
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

	@media (max-width: 700px) {
		.links {
			display: grid;
			gap: var(--space-3);
		}
	}
</style>