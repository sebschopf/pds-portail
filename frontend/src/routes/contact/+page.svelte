<script lang="ts">
	let concerne = $state('surveillance');
	let email = $state('');
	let message = $state('');
	let loading = $state(false);
	let sent = $state(false);
	let error = $state<string | null>(null);

	const options = [
		{ value: 'surveillance', label: 'Problème de surveillance' },
		{ value: 'paiement', label: 'Problème de paiement' },
		{ value: 'donnees', label: 'Question sur les données' },
		{ value: 'technique', label: 'Problème technique' },
		{ value: 'autre', label: 'Autre demande' }
	];

	async function handleSubmit(e: Event) {
		e.preventDefault();
		loading = true;
		error = null;
		try {
			const res = await fetch('/api/v1/contact', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ concerne, email, message })
			});
			if (res.ok) {
				sent = true;
			} else {
				error = 'Une erreur est survenue. Veuillez réessayer.';
			}
		} catch {
			error = 'Erreur de connexion. Veuillez réessayer.';
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Contact — PDS Portail</title>
</svelte:head>

<article class="contact-page">
	<h1>Contact</h1>

	{#if sent}
		<div class="success-box" role="status">
			<p>Votre message a été envoyé. Nous vous répondrons dans les meilleurs délais.</p>
			<p><a href="/">Retour à l'accueil</a></p>
		</div>
	{:else}
		<p class="intro">
			Une question, un problème technique, une remarque sur les données ?
			Remplissez ce formulaire et nous vous répondrons par email.
		</p>

		<form onsubmit={handleSubmit} class="contact-form">
			<div class="form-group">
				<label for="concerne">Concerne</label>
				<select id="concerne" bind:value={concerne} required>
					{#each options as opt (opt.value)}
						<option value={opt.value}>{opt.label}</option>
					{/each}
				</select>
			</div>

			<div class="form-group">
				<label for="contact-email">Votre adresse email (pour la réponse)</label>
				<input
					id="contact-email"
					type="email"
					bind:value={email}
					placeholder="vous@exemple.ch"
					required
					autocomplete="email"
				/>
			</div>

			<div class="form-group">
				<label for="contact-message">Votre message</label>
				<textarea
					id="contact-message"
					bind:value={message}
					placeholder="Décrivez votre demande ou vos difficultés…"
					rows={6}
					required
					minlength={10}
					maxlength={5000}
				></textarea>
			</div>

			{#if error}
				<p class="error-message" role="alert">{error}</p>
			{/if}

			<button type="submit" disabled={loading || !email || !message}>
				{loading ? 'Envoi en cours…' : 'Envoyer'}
			</button>
		</form>
	{/if}

	<p class="back-link">
		<a href="/">← Retour à l'accueil</a>
	</p>
</article>

<style>
	.contact-page {
		max-width: 60ch;
		margin: 0 auto;
	}

	h1 {
		font-family: var(--font-display);
		font-size: var(--font-size-heading-xl);
		margin: 0 0 var(--space-4);
	}

	.intro {
		font-size: var(--font-size-body);
		color: var(--color-on-surface-muted);
		margin-bottom: var(--space-5);
		line-height: var(--line-height-relaxed);
	}

	.contact-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.form-group label {
		font-weight: 600;
		font-size: var(--font-size-body);
	}

	.form-group input,
	.form-group select,
	.form-group textarea {
		padding: var(--space-2) var(--space-3);
		border: var(--border-thin) solid var(--color-outline);
		border-radius: var(--radius-none);
		font-size: var(--font-size-body);
		font-family: inherit;
		background: var(--color-surface);
		color: var(--color-on-surface);
	}

	.form-group textarea {
		resize: vertical;
		min-height: 8rem;
	}

	form button {
		padding: var(--space-3) var(--space-5);
		background: var(--color-primary);
		color: white;
		border: none;
		border-radius: var(--radius-none);
		font-weight: 600;
		font-size: var(--font-size-body);
		cursor: pointer;
		align-self: flex-start;
		transition: background var(--duration-fast) var(--easing-standard);
	}

	form button:hover:not(:disabled) {
		background: var(--color-primary-container);
	}

	form button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.success-box {
		padding: var(--space-5);
		background: var(--color-success-subtle);
		border: var(--border-thin) solid var(--color-success);
		border-radius: var(--radius-none);
		text-align: center;
	}

	.success-box p {
		margin: 0 0 var(--space-3) 0;
		font-size: var(--font-size-body);
		line-height: var(--line-height-relaxed);
	}

	.success-box a {
		color: var(--color-primary);
		font-weight: 600;
	}

	.error-message {
		color: var(--color-error);
		font-size: var(--font-size-body);
		margin: 0;
	}

	.back-link {
		margin-top: var(--space-6);
		padding-top: var(--space-4);
		border-top: var(--border-thin) solid var(--color-border);
	}

	.back-link a {
		font-weight: 650;
		color: var(--color-primary);
	}
</style>