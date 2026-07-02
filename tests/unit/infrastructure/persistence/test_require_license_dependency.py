"""Tests de la dépendance FastAPI require_license (PDS-81, ADR-027)."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.license_repository import SqlAlchemyLicenseRepository
from app.infrastructure.persistence.models import LicenseModel
from app.presentation.api.dependencies import require_license


@pytest.mark.asyncio
class TestRequireLicenseDependency:
    """Tests pour la dépendance FastAPI require_license."""

    async def test_require_license_missing_header(self) -> None:
        """Teste 401 si header X-API-Key manquant."""
        with pytest.raises(HTTPException) as exc_info:
            await require_license(x_api_key=None)  # type: ignore

        assert exc_info.value.status_code == 401
        assert "Missing X-API-Key" in exc_info.value.detail

    async def test_require_license_invalid_key(self) -> None:
        """Teste 401 si clé invalide."""
        with pytest.raises(HTTPException) as exc_info:
            await require_license(x_api_key="invalid_key")

        assert exc_info.value.status_code == 401
        assert "Invalid or expired" in exc_info.value.detail

    async def test_require_license_valid_key(self) -> None:
        """Teste que clé valide retourne License et incrémente usage."""
        key = str(uuid.uuid4())
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        repo = SqlAlchemyLicenseRepository()

        license_obj = repo.create(
            key_hash=key_hash,
            plan="basic",
            quota_monthly=100,
            expires_at=None,
        )

        result = await require_license(x_api_key=key)

        assert result.id == license_obj.id
        assert result.plan == "basic"

        # Vérifie que l'usage a été incrémenté
        with SessionLocal() as session:
            license_model = session.get(LicenseModel, license_obj.id)
            assert license_model is not None
            assert license_model.used_this_month == 1

        # Cleanup
        with SessionLocal() as session:
            session.query(LicenseModel).filter(LicenseModel.id == license_obj.id).delete()
            session.commit()

    async def test_require_license_quota_exceeded(self) -> None:
        """Teste 429 si quota épuisé."""
        key = str(uuid.uuid4())
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        repo = SqlAlchemyLicenseRepository()

        license_obj = repo.create(
            key_hash=key_hash,
            plan="basic",
            quota_monthly=1,
            expires_at=None,
        )

        # Épuise le quota
        with SessionLocal() as session:
            license_model = session.get(LicenseModel, license_obj.id)
            if license_model:
                license_model.used_this_month = 1
                session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await require_license(x_api_key=key)

        assert exc_info.value.status_code == 429
        assert "quota exceeded" in exc_info.value.detail
        assert exc_info.value.headers is not None
        assert "Retry-After" in exc_info.value.headers

        # Cleanup
        with SessionLocal() as session:
            session.query(LicenseModel).filter(LicenseModel.id == license_obj.id).delete()
            session.commit()

    async def test_require_license_expired_key(self) -> None:
        """Teste 401 si clé expirée."""
        key = str(uuid.uuid4())
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        reference_now = datetime(2026, 7, 2, tzinfo=UTC)
        expired_date = (reference_now - timedelta(days=1)).isoformat()
        repo = SqlAlchemyLicenseRepository()

        license_obj = repo.create(
            key_hash=key_hash,
            plan="basic",
            quota_monthly=100,
            expires_at=expired_date,
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_license(x_api_key=key)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired" in exc_info.value.detail

        # Cleanup
        with SessionLocal() as session:
            session.query(LicenseModel).filter(LicenseModel.id == license_obj.id).delete()
            session.commit()
