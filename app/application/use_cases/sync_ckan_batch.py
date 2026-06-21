"""Cas d'usage de synchronisation d'un lot CKAN vers le cache local."""

import logging
from datetime import UTC, datetime

from app.application.errors.ingestion import CkanRateLimitError, CkanTimeoutError
from app.application.ports.cache_repository import CacheRepositoryPort
from app.application.ports.ckan_client import CkanClientPort
from app.application.ports.ckan_types import (
    CkanPackagePayload,
    CkanPackageSearchResponse,
    CkanTagPayload,
)
from app.domain.ckan_normalized import Dataset, NormalizedBatch, Organization, Resource
from app.domain.quality_indicators import DatasetIndicatorInput, compute_indicators

logger = logging.getLogger(__name__)


class SyncCkanBatchUseCase:
    """Orchestre lecture CKAN, normalisation domaine et persistence.

    La responsabilite du use case reste volontairement limitee a la coordination.
    Le client gere l'acces distant, le parseur verrouille les payloads et le
    repository s'occupe de l'upsert.
    """

    def __init__(self, client: CkanClientPort, repository: CacheRepositoryPort) -> None:
        self._client = client
        self._repository = repository

    def execute(self, start: int = 0, rows: int = 100) -> NormalizedBatch:
        """Synchronise une page CKAN complete puis retourne le batch normalise."""

        if rows <= 0:
            raise ValueError(f"rows doit etre > 0, recu {rows}")
        if start < 0:
            raise ValueError(f"start doit etre >= 0, recu {start}")

        # La resilience reseau (backoff, retry) est dans le client.
        # Le use case ne fait que skipper ce que le client n'a pas pu recuperer
        # apres epuisement des tentatives, on ne surcharge pas les serveurs d'Etat.
        try:
            payload = self._client.fetch_packages_batch(start=start, rows=rows)
        except CkanTimeoutError:
            logger.warning("Timeout sur le lot CKAN start=%s rows=%s, lot ignore", start, rows)
            return NormalizedBatch(organizations=[], datasets=[], resources=[])
        except CkanRateLimitError:
            logger.warning(
                "Rate limit persistant sur le lot CKAN start=%s rows=%s, lot ignore", start, rows
            )
            return NormalizedBatch(organizations=[], datasets=[], resources=[])

        batch = self._normalize(payload)
        self._repository.upsert_normalized_batch(batch)
        return batch

    def _normalize(self, payload: CkanPackageSearchResponse) -> NormalizedBatch:
        """Traduit le payload CKAN typé en entites du domaine."""

        result_payload = payload.get("result")
        results = result_payload.get("results", []) if result_payload else []
        synced_at = datetime.now(UTC).isoformat()

        organizations: dict[str, Organization] = {}
        datasets: list[Dataset] = []
        resources: list[Resource] = []

        for item in results:
            organization_payload = item.get("organization") or {}
            organization_id = organization_payload.get("id") or organization_payload.get("name")
            if not organization_id:
                logger.warning("Dataset ignore sans organisation id/name")
                continue

            # Construite une seule fois a la premiere occurrence. CKAN garantit que
            # les metadonnees (name, description, url) sont identiques pour tous les
            # datasets d'une meme organisation, donc les occurrences suivantes sont
            # ignorees sans perte d'information.
            if organization_id not in organizations:
                organizations[organization_id] = Organization(
                    id=organization_id,
                    name=organization_payload.get("title")
                    or organization_payload.get("name")
                    or organization_id,
                    description=organization_payload.get("description"),
                    ckan_url=organization_payload.get("image_url")
                    or organization_payload.get("url"),
                    last_synced=synced_at,
                )

            dataset_id = item.get("id")
            title = item.get("title")
            if not dataset_id or not title:
                logger.warning("Dataset invalide ignore (id/title manquant)")
                continue

            tags = self._extract_tags(item)
            resource_formats: list[str] = []

            for resource_payload in item.get("resources", []):
                resource_id = resource_payload.get("id")
                resource_name = (
                    resource_payload.get("name")
                    or resource_payload.get("description")
                    or resource_id
                )
                if not resource_id or not resource_name:
                    logger.warning("Ressource invalide ignoree pour dataset=%s", dataset_id)
                    continue

                resource_format = resource_payload.get("format")
                if resource_format:
                    resource_formats.append(resource_format)

                resources.append(
                    Resource(
                        id=resource_id,
                        dataset_id=dataset_id,
                        name=resource_name,
                        format=resource_format,
                        url=resource_payload.get("url"),
                        size_bytes=resource_payload.get("size"),
                        created=resource_payload.get("created"),
                        last_modified=resource_payload.get("last_modified"),
                    )
                )

            indicators = compute_indicators(
                DatasetIndicatorInput(
                    description=item.get("notes"),
                    tags=tags,
                    created=item.get("metadata_created"),
                    modified=item.get("metadata_modified"),
                    resource_formats=resource_formats,
                    resource_count=len(resource_formats),
                )
            )

            datasets.append(
                Dataset(
                    id=dataset_id,
                    org_id=organization_id,
                    title=title,
                    description=item.get("notes"),
                    tags=tags,
                    created=item.get("metadata_created"),
                    modified=item.get("metadata_modified"),
                    quality_score=indicators.quality_score,
                    completeness=indicators.completeness,
                    freshness_days=indicators.freshness_days,
                    ckan_url=item.get("url"),
                    normalized_at=synced_at,
                )
            )

        return NormalizedBatch(
            organizations=list(organizations.values()),
            datasets=datasets,
            resources=resources,
        )

    def _extract_tags(self, item: CkanPackagePayload) -> list[str]:
        """Ne conserve que les libelles exploitables pour la recherche locale."""

        tags: list[str] = []
        for tag in item.get("tags", []):
            value = self._tag_value(tag)
            if value:
                tags.append(value)
        return tags

    def _tag_value(self, tag: CkanTagPayload) -> str | None:
        """Prefere ``display_name`` quand CKAN fournit un libelle humain."""

        return tag.get("display_name") or tag.get("name")
