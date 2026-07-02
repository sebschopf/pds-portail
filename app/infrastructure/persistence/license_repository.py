"""Repository pour la gestion des licences API (ADR-027, SPEC-008).

Implémentation SQLAlchemy du port LicenseRepositoryPort.
Gère les clés API hashées, les quotas mensuels et les taux d'utilisation.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.application.ports.license_repository import License
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import LicenseModel

logger = logging.getLogger(__name__)


class SqlAlchemyLicenseRepository:
    """Repository pour les licences API (clés d'accès)."""

    def find_by_key_hash(self, key_hash: str) -> License | None:
        """Cherche une licence par le hash SHA-256 de sa clé.

        Vérifie également que la licence n'est pas expirée.
        """
        try:
            with SessionLocal() as session:
                stmt = select(LicenseModel).where(LicenseModel.key_hash == key_hash)
                model = session.execute(stmt).scalar_one_or_none()

                if not model:
                    return None

                # Vérifie l'expiration
                if model.expires_at:
                    expires_dt = datetime.fromisoformat(model.expires_at)
                    now_dt = datetime.now(UTC)
                    if now_dt >= expires_dt:
                        logger.info(f"License {model.id} has expired.")
                        return None

                # Note: quota check is done in increment_usage(), not here.
                # This allows require_license() to raise 429 on quota exceeded.

                return License(
                    id=model.id,
                    key_hash=model.key_hash,
                    plan=model.plan,
                    quota_monthly=model.quota_monthly,
                    used_this_month=model.used_this_month,
                    created_at=model.created_at,
                    expires_at=model.expires_at,
                )
        except Exception as e:
            logger.exception(f"Error finding license by key_hash: {e}")
            return None

    def increment_usage(self, license_id: str) -> None:
        """Incrémente `used_this_month` pour une licence.

        Lève une exception si le quota est dépassé après incrément.
        """
        try:
            with SessionLocal() as session:
                stmt = select(LicenseModel).where(LicenseModel.id == license_id)
                license_model = session.execute(stmt).scalar_one_or_none()

                if not license_model:
                    raise ValueError(f"License {license_id} not found.")

                if license_model.used_this_month >= license_model.quota_monthly:
                    raise ValueError(
                        f"License {license_id} quota exceeded "
                        f"({license_model.used_this_month}/{license_model.quota_monthly})."
                    )

                license_model.used_this_month += 1
                session.commit()
                logger.debug(
                    f"Incremented usage for license {license_id} "
                    f"to {license_model.used_this_month}."
                )
        except IntegrityError as e:
            logger.exception(f"Integrity error incrementing usage for {license_id}: {e}")
            raise ValueError(f"Failed to increment usage for license {license_id}.") from e
        except Exception as e:
            logger.exception(f"Error incrementing usage for {license_id}: {e}")
            raise

    def create(
        self,
        key_hash: str,
        plan: str,
        quota_monthly: int,
        expires_at: str | None = None,
    ) -> License:
        """Crée une nouvelle licence.

        Utilise un UUID v4 pour l'ID.
        """
        try:
            with SessionLocal() as session:
                import uuid

                now_iso = datetime.now(UTC).isoformat()
                license_id = str(uuid.uuid4())

                license_model = LicenseModel(
                    id=license_id,
                    key_hash=key_hash,
                    plan=plan,
                    quota_monthly=quota_monthly,
                    used_this_month=0,
                    created_at=now_iso,
                    expires_at=expires_at,
                )

                session.add(license_model)
                session.commit()

                logger.info(f"Created license {license_id} with plan={plan}.")

                return License(
                    id=license_model.id,
                    key_hash=license_model.key_hash,
                    plan=license_model.plan,
                    quota_monthly=license_model.quota_monthly,
                    used_this_month=license_model.used_this_month,
                    created_at=license_model.created_at,
                    expires_at=license_model.expires_at,
                )
        except IntegrityError as e:
            logger.exception(f"Integrity error creating license: {e}")
            raise ValueError("License key_hash already exists.") from e
        except Exception as e:
            logger.exception(f"Error creating license: {e}")
            raise

    def reset_monthly_usage(self) -> None:
        """Réinitialise `used_this_month` à 0 pour toutes les licences.

        À appeler le 1er du mois (tâche batch).
        """
        try:
            with SessionLocal() as session:
                stmt = select(LicenseModel)
                licenses = session.execute(stmt).scalars().all()

                for license_model in licenses:
                    license_model.used_this_month = 0

                session.commit()

                logger.info(f"Reset monthly usage for {len(licenses)} licenses.")
        except Exception as e:
            logger.exception(f"Error resetting monthly usage: {e}")
            raise
