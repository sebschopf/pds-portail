"""Normalisateur CKAN — traduit un payload CKAN en entités domaine.

Implémente le contrat ``NormalizerPort`` pour la source ``"ckan"``.
Extrait depuis ``SyncCkanBatchUseCase._normalize()`` (PDS-126) pour rendre
la normalisation paramétrable par source.
"""

import logging
import re
import unicodedata
from datetime import UTC, datetime

from app.application.ports.ckan_types import (
    CkanPackagePayload,
    CkanPackageSearchResponse,
    CkanTagPayload,
)
from app.application.ports.normalizer_port import NormalizerPort
from app.domain.ckan_normalized import Dataset, NormalizedBatch, Organization, Resource
from app.domain.quality_indicators import DatasetIndicatorInput, compute_indicators

logger = logging.getLogger(__name__)


class CkanNormalizer(NormalizerPort):
    """Normalisateur CKAN : traduit un payload opendata.swiss en entités domaine.

    Le paramètre ``source`` (par défaut ``"ckan"``) est propagé dans chaque
    entité normalisée. Cela permet de changer la valeur (ex: ``"i14y"``)
    sans modifier la logique de normalisation.
    """

    def __init__(self, source: str = "ckan") -> None:
        self._source = source

    def normalize(self, payload: CkanPackageSearchResponse) -> NormalizedBatch:
        """Traduit un payload CKAN typé en entités du domaine."""
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
                logger.warning("Dataset ignoré sans organisation id/name")
                continue

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
                    source=self._source,
                )

            dataset_id = item.get("id")
            title = item.get("title")
            if not dataset_id or not title:
                logger.warning("Dataset invalide ignoré (id/title manquant)")
                continue

            tags = self._extract_tags(item)
            resource_formats: list[str] = []
            resource_last_modified_dates: list[str] = []

            for resource_payload in item.get("resources", []):
                resource_id = resource_payload.get("id")
                resource_name = (
                    resource_payload.get("name")
                    or resource_payload.get("description")
                    or resource_id
                )
                if not resource_id or not resource_name:
                    logger.warning("Ressource invalide ignorée pour dataset=%s", dataset_id)
                    continue

                resource_format = resource_payload.get("format")
                if resource_format:
                    resource_formats.append(resource_format)

                last_mod = resource_payload.get("last_modified")
                if last_mod:
                    resource_last_modified_dates.append(last_mod)

                resources.append(
                    Resource(
                        id=resource_id,
                        dataset_id=dataset_id,
                        name=resource_name,
                        format=resource_format,
                        url=resource_payload.get("url"),
                        size_bytes=resource_payload.get("size"),
                        created=resource_payload.get("created"),
                        last_modified=last_mod,
                        source=self._source,
                    )
                )

            effective_modified = (
                max(resource_last_modified_dates)
                if resource_last_modified_dates
                else item.get("metadata_created")
            )

            indicators = compute_indicators(
                DatasetIndicatorInput(
                    description=item.get("notes"),
                    tags=tags,
                    created=item.get("metadata_created"),
                    modified=effective_modified,
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
                    modified=effective_modified,
                    quality_score=indicators.quality_score,
                    completeness=indicators.completeness,
                    freshness_days=indicators.freshness_days,
                    ckan_url=item.get("url"),
                    normalized_at=synced_at,
                    source=self._source,
                )
            )

        return NormalizedBatch(
            organizations=list(organizations.values()),
            datasets=datasets,
            resources=resources,
        )

    def _extract_tags(self, item: CkanPackagePayload) -> list[str]:
        """Ne conserve que les libellés exploitables pour la recherche locale."""
        tags: list[str] = []
        seen: set[str] = set()
        for tag in item.get("tags", []):
            value = self._tag_value(tag)
            if value and value not in seen:
                tags.append(value)
                seen.add(value)
        return tags

    def _tag_value(self, tag: CkanTagPayload) -> str | None:
        """Préfère ``display_name`` quand CKAN fournit un libellé humain."""
        raw = tag.get("display_name") or tag.get("name")
        if not raw:
            return None
        return _normalize_tag(raw)


def _normalize_tag(raw: object) -> str | None:
    """Normalise un tag CKAN pour réduire les doublons sémantiques.

    Règles appliquées:
    - trim + lower
    - suppression des accents (NFKD)
    - espaces multiples compactés
    """
    if not isinstance(raw, str):
        return None

    value = raw.strip().lower()
    if not value:
        return None
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"\s+", " ", value).strip()
    return value or None
