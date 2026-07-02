"""Dépendance FastAPI pour valider les clés API (middleware d'authentification).

Extrait le header X-API-Key, hash la clé, la cherche en base, et retourne
la licence ou lève une HTTPException (401 ou 429).
"""

import hashlib
import logging

from fastapi import Header, HTTPException

from app.application.ports.license_repository import License
from app.infrastructure.persistence.license_repository import (
    SqlAlchemyLicenseRepository,
)

logger = logging.getLogger(__name__)


async def require_license(x_api_key: str = Header(None)) -> License:
    """Valide une clé API X-API-Key et retourne la licence.

    Lève :
    - HTTPException 401 si la clé est manquante, invalide ou expirée.
    - HTTPException 429 si le quota mensuel est épuisé.
    """
    if not x_api_key:
        logger.warning("Missing X-API-Key header")
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header",
        )

    # Hash la clé en SHA-256
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()

    # Cherche la licence
    repository = SqlAlchemyLicenseRepository()
    license_obj = repository.find_by_key_hash(key_hash)

    if not license_obj:
        logger.warning(f"Invalid or expired API key (hash prefix: {key_hash[:8]}...)")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key",
        )

    # Incrémente l'usage
    try:
        repository.increment_usage(license_obj.id)
    except ValueError as e:
        logger.warning(f"License quota exceeded: {e}")
        raise HTTPException(
            status_code=429,
            detail="Monthly quota exceeded for this API key",
            headers={
                "Retry-After": "2592000",  # 30 jours en secondes
            },
        ) from e

    return license_obj
