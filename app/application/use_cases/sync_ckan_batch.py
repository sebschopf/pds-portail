"""Cas d'usage de synchronisation d'un lot CKAN vers le cache local."""

import logging

from app.application.errors.ingestion import CkanRateLimitError, CkanTimeoutError
from app.application.ports.cache_repository import CacheRepositoryPort
from app.application.ports.ckan_client import CkanClientPort
from app.application.ports.normalizer_port import NormalizerPort
from app.domain.ckan_normalized import NormalizedBatch

logger = logging.getLogger(__name__)


class SyncCkanBatchUseCase:
    """Orchestre lecture CKAN, normalisation domaine et persistence.

    La responsabilite du use case reste volontairement limitee a la coordination.
    Le client gere l'acces distant, le normalisateur traduit le payload source
    en entites domaine, et le repository s'occupe de l'upsert.

    Le normalisateur est injecte (PDS-126) pour permettre de brancher differentes
    sources (CKAN, I14Y, metadata.swiss) sans modifier le pipeline.
    """

    def __init__(
        self,
        client: CkanClientPort,
        repository: CacheRepositoryPort,
        normalizer: NormalizerPort | None = None,
    ) -> None:
        self._client = client
        self._repository = repository
        # Import tardif pour eviter l'import circulaire au niveau module.
        # Le normalisateur CKAN est le defaut, mais peut etre remplace
        # pour une autre source (test, I14Y future, etc.)
        if normalizer is None:
            from app.domain.ckan_normalizer import CkanNormalizer

            normalizer = CkanNormalizer(source="ckan")
        self._normalizer = normalizer

    def execute(
        self,
        start: int = 0,
        rows: int = 100,
        modified_since: str | None = None,
    ) -> NormalizedBatch:
        """Synchronise une page CKAN complete puis retourne le batch normalise.

        Si ``modified_since`` est fourni (ISO 8601), utilise le filtre
        ``fq=metadata_modified`` pour la synchro differentielle (PDS-53).
        """

        if rows <= 0:
            raise ValueError(f"rows doit etre > 0, recu {rows}")
        if start < 0:
            raise ValueError(f"start doit etre >= 0, recu {start}")

        # La resilience reseau (backoff, retry) est dans le client.
        # Le use case ne fait que skipper ce que le client n'a pas pu recuperer
        # apres epuisement des tentatives, on ne surcharge pas les serveurs d'Etat.
        try:
            payload = self._client.fetch_packages_batch(
                start=start, rows=rows, modified_since=modified_since
            )
        except CkanTimeoutError:
            logger.warning("Timeout sur le lot CKAN start=%s rows=%s, lot ignore", start, rows)
            return NormalizedBatch(organizations=[], datasets=[], resources=[])
        except CkanRateLimitError:
            logger.warning(
                "Rate limit persistant sur le lot CKAN start=%s rows=%s, lot ignore", start, rows
            )
            return NormalizedBatch(organizations=[], datasets=[], resources=[])

        batch = self._normalizer.normalize(payload)
        self._repository.upsert_normalized_batch(batch)
        return batch
