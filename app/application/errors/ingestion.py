"""Erreurs applicatives liees a l'ingestion CKAN."""


class CkanIngestionError(Exception):
    """Base des erreurs applicatives d'ingestion CKAN."""


class CkanRateLimitError(CkanIngestionError):
    """Le service CKAN a repondu 429 apres les retries."""


class CkanTimeoutError(CkanIngestionError):
    """La requete CKAN a depasse le delai imparti."""
