<script lang="ts">
  import type { ResourceContract } from '$lib/contracts/dataset-detail';
  import { appendSearchContext } from '$lib/navigation/search-context';
  import { getSafeExternalUrl } from '$lib/security/external-url';

  let {
    resources,
    searchContext = null
  }: {
    resources: ResourceContract[];
    searchContext?: string | null;
  } = $props();

  const hasResources = $derived(resources.length > 0);

  function formatSize(bytes: number | null): string | null {
    if (bytes === null || bytes === undefined) {
      return null;
    }

    if (bytes < 1000) {
      return `${bytes} B`;
    }

    if (bytes < 1_000_000) {
      return `${(bytes / 1000).toFixed(1)} KB`;
    }

    return `${(bytes / 1_000_000).toFixed(1)} MB`;
  }

  function formatDate(value: string | null): string | null {
    if (!value) {
      return null;
    }

    const date = new Date(value);
    if (Number.isNaN(date.valueOf())) {
      return value;
    }

    return date.toISOString().slice(0, 10);
  }
</script>

<section class="resource-block" aria-label="Ressources associees">
  <h3 class="resource-heading">Ressources associees</h3>

  {#if hasResources}
    <div class="resource-list">
      {#each resources as resource, idx (`${resource.id}-${idx}`)}
        <article class="resource-item">
          <div class="resource-header">
            <div class="resource-ident">
              <h4 class="resource-name">{resource.name}</h4>
              {#if resource.url}
                <p class="resource-url">{resource.url}</p>
              {/if}
            </div>
            <span class="resource-format">{resource.format ?? 'Inconnu'}</span>
          </div>

          <dl class="resource-meta" aria-label={`Meta ressource ${resource.name}`}>
            {#if resource.size_bytes !== null}
              <div>
                <dt>Taille</dt>
                <dd>{formatSize(resource.size_bytes)}</dd>
              </div>
            {/if}
            {#if resource.created}
              <div>
                <dt>Creation</dt>
                <dd>{formatDate(resource.created)}</dd>
              </div>
            {/if}
            {#if resource.last_modified}
              <div>
                <dt>Derniere modification</dt>
                <dd>{formatDate(resource.last_modified)}</dd>
              </div>
            {/if}
          </dl>

          <nav class="resource-links" aria-label={`Navigation ressource ${resource.name}`}>
            <a href={appendSearchContext(`/resource/${encodeURIComponent(resource.id)}`, searchContext)}
              >Consulter la ressource</a
            >
            {#if getSafeExternalUrl(resource.url)}
              <a href={getSafeExternalUrl(resource.url)} target="_blank" rel="noreferrer noopener"
                >Ouvrir l URL source</a
              >
            {:else if resource.url}
              <span class="resource-link-disabled" role="status">URL source non conforme</span>
            {/if}
          </nav>
        </article>
      {/each}
    </div>
  {:else}
    <p class="resource-empty" role="status">Aucune ressource associee disponible</p>
  {/if}
</section>

<style>
  .resource-block {
    margin-top: var(--space-5);
  }

  .resource-heading {
    margin: 0 0 var(--space-3);
		font-size: var(--font-size-heading-md);
    line-height: var(--line-height-title);
  }

  .resource-list {
    display: grid;
    gap: var(--space-4);
  }

  .resource-empty {
    margin: 0;
    padding: var(--space-3) var(--space-4);
    background: var(--color-surface-muted);
    border: var(--border-thin) dashed var(--color-border);
    border-radius: var(--radius-none);
    color: var(--color-on-surface-soft);
  }

  .resource-item {
    padding: var(--space-4);
    border: var(--border-thin) solid var(--color-border);
    border-radius: var(--radius-none);
    background: var(--color-surface);
  }

  .resource-header {
    display: flex;
    justify-content: space-between;
    gap: var(--space-4);
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .resource-ident {
    display: grid;
    gap: var(--space-1);
  }

  .resource-name {
    margin: 0;
		font-size: var(--font-size-heading-sm);
		line-height: var(--line-height-body);
    word-break: break-word;
  }

  .resource-url {
    margin: 0;
    font-size: var(--font-size-ui);
    color: var(--color-on-surface-subtle);
    overflow-wrap: anywhere;
  }

  .resource-format {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-none);
    border: var(--border-thin) solid var(--color-border);
    background: color-mix(in oklch, var(--color-primary) 12%, var(--color-surface));
    font-size: var(--font-size-ui);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    white-space: nowrap;
  }

  .resource-meta {
    margin: var(--space-4) 0 0;
    display: grid;
    gap: var(--space-3);
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  }

  dt {
    margin: 0;
    font-size: var(--font-size-ui);
    font-weight: 700;
    color: var(--color-on-surface-subtle);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  dd {
    margin: var(--space-1) 0 0;
    font-size: var(--font-size-ui);
    overflow-wrap: anywhere;
  }

  .resource-links {
    display: flex;
    gap: var(--space-4);
    flex-wrap: wrap;
    margin-top: var(--space-4);
  }

  .resource-links a {
    font-weight: 650;
    text-decoration-thickness: 2px;
    overflow-wrap: anywhere;
  }

  .resource-link-disabled {
    font-size: var(--font-size-ui);
    color: var(--color-on-surface-subtle);
  }

  @media (max-width: 43.75rem) {
    .resource-links {
      display: grid;
      gap: var(--space-3);
    }
  }
</style>
