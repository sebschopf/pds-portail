"""Tests CRUD pour le repository des licences API (PDS-81, ADR-027)."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.application.ports.license_repository import License
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.license_repository import SqlAlchemyLicenseRepository
from app.infrastructure.persistence.models import LicenseModel


@pytest.fixture
def repository() -> SqlAlchemyLicenseRepository:
    """Fixture fournissant une instance du repository."""
    return SqlAlchemyLicenseRepository()


@pytest.fixture
def valid_license_key() -> str:
    """Génère une clé UUID valide."""
    return str(uuid.uuid4())


class TestLicenseRepositoryFindByKeyHash:
    """Tests pour la méthode find_by_key_hash."""

    def test_find_existing_license(
        self,
        repository: SqlAlchemyLicenseRepository,
        valid_license_key: str,
    ) -> None:
        """Teste la recherche d'une licence existante."""
        key_hash = hashlib.sha256(valid_license_key.encode()).hexdigest()
        license_obj = repository.create(
            key_hash=key_hash,
            plan="basic",
            quota_monthly=100,
            expires_at=None,
        )

        found_license = repository.find_by_key_hash(key_hash)

        assert found_license is not None
        assert found_license.id == license_obj.id
        assert found_license.plan == "basic"
        assert found_license.quota_monthly == 100

        # Cleanup
        with SessionLocal() as session:
            session.query(LicenseModel).filter(LicenseModel.id == license_obj.id).delete()
            session.commit()

    def test_find_nonexistent_license(
        self,
        repository: SqlAlchemyLicenseRepository,
    ) -> None:
        """Teste la recherche d'une licence inexistante."""
        nonexistent_hash = hashlib.sha256(b"nonexistent").hexdigest()
        found_license = repository.find_by_key_hash(nonexistent_hash)

        assert found_license is None

    def test_find_expired_license(
        self,
        repository: SqlAlchemyLicenseRepository,
    ) -> None:
        """Teste qu'une licence expirée n'est pas trouvée."""
        expired_key = str(uuid.uuid4())
        key_hash = hashlib.sha256(expired_key.encode()).hexdigest()
        reference_now = datetime(2026, 7, 2, tzinfo=UTC)
        expired_date = (reference_now - timedelta(days=1)).isoformat()

        license_obj = repository.create(
            key_hash=key_hash,
            plan="basic",
            quota_monthly=100,
            expires_at=expired_date,
        )

        found = repository.find_by_key_hash(key_hash)

        assert found is None

        # Cleanup
        with SessionLocal() as session:
            session.query(LicenseModel).filter(LicenseModel.id == license_obj.id).delete()
            session.commit()

    def test_find_quota_not_checked(
        self,
        repository: SqlAlchemyLicenseRepository,
    ) -> None:
        """Teste que find_by_key_hash ne vérifie PAS le quota.

        C'est increment_usage qui valide le quota.
        """
        key = str(uuid.uuid4())
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        license_obj = repository.create(
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

        found = repository.find_by_key_hash(key_hash)

        assert found is not None
        assert found.id == license_obj.id
        assert found.used_this_month == 1

        # Cleanup
        with SessionLocal() as session:
            session.query(LicenseModel).filter(LicenseModel.id == license_obj.id).delete()
            session.commit()


class TestLicenseRepositoryIncrementUsage:
    """Tests pour la méthode increment_usage."""

    def test_increment_usage_success(
        self,
        repository: SqlAlchemyLicenseRepository,
        valid_license_key: str,
    ) -> None:
        """Teste l'incrément réussi du usage."""
        key_hash = hashlib.sha256(valid_license_key.encode()).hexdigest()
        license_obj = repository.create(
            key_hash=key_hash,
            plan="basic",
            quota_monthly=100,
            expires_at=None,
        )

        repository.increment_usage(license_obj.id)

        with SessionLocal() as session:
            license_model = session.get(LicenseModel, license_obj.id)
            assert license_model is not None
            assert license_model.used_this_month == 1

        # Cleanup
        with SessionLocal() as session:
            session.query(LicenseModel).filter(LicenseModel.id == license_obj.id).delete()
            session.commit()

    def test_increment_usage_quota_exceeded(
        self,
        repository: SqlAlchemyLicenseRepository,
        valid_license_key: str,
    ) -> None:
        """Teste que l'incrément échoue quand le quota est épuisé."""
        key_hash = hashlib.sha256(valid_license_key.encode()).hexdigest()
        license_obj = repository.create(
            key_hash=key_hash,
            plan="basic",
            quota_monthly=1,
            expires_at=None,
        )

        # Première utilisation → succès
        repository.increment_usage(license_obj.id)

        # Deuxième utilisation → quota exceeded
        with pytest.raises(ValueError, match="quota exceeded"):
            repository.increment_usage(license_obj.id)

        # Cleanup
        with SessionLocal() as session:
            session.query(LicenseModel).filter(LicenseModel.id == license_obj.id).delete()
            session.commit()

    def test_increment_usage_nonexistent(
        self,
        repository: SqlAlchemyLicenseRepository,
    ) -> None:
        """Teste que l'incrément échoue pour une licence inexistante."""
        with pytest.raises(ValueError, match="not found"):
            repository.increment_usage("nonexistent_id")


class TestLicenseRepositoryCreate:
    """Tests pour la méthode create."""

    def test_create_license_success(
        self,
        repository: SqlAlchemyLicenseRepository,
        valid_license_key: str,
    ) -> None:
        """Teste la création réussie d'une licence."""
        key_hash = hashlib.sha256(valid_license_key.encode()).hexdigest()

        license_obj = repository.create(
            key_hash=key_hash,
            plan="pro",
            quota_monthly=1000,
            expires_at=None,
        )

        assert license_obj.id is not None
        assert license_obj.plan == "pro"
        assert license_obj.quota_monthly == 1000
        assert license_obj.used_this_month == 0
        assert license_obj.expires_at is None

        # Cleanup
        with SessionLocal() as session:
            session.query(LicenseModel).filter(LicenseModel.id == license_obj.id).delete()
            session.commit()

    def test_create_license_duplicate_key(
        self,
        repository: SqlAlchemyLicenseRepository,
        valid_license_key: str,
    ) -> None:
        """Teste que la création échoue avec une clé dupliquée."""
        key_hash = hashlib.sha256(valid_license_key.encode()).hexdigest()

        license_obj = repository.create(
            key_hash=key_hash,
            plan="basic",
            quota_monthly=100,
        )

        with pytest.raises(ValueError, match="already exists"):
            repository.create(
                key_hash=key_hash,
                plan="pro",
                quota_monthly=1000,
            )

        # Cleanup
        with SessionLocal() as session:
            session.query(LicenseModel).filter(LicenseModel.id == license_obj.id).delete()
            session.commit()


class TestLicenseRepositoryResetMonthlyUsage:
    """Tests pour la méthode reset_monthly_usage."""

    def test_reset_monthly_usage(
        self,
        repository: SqlAlchemyLicenseRepository,
    ) -> None:
        """Teste la réinitialisation du usage mensuel."""
        keys = [str(uuid.uuid4()) for _ in range(2)]
        hashes = [hashlib.sha256(key.encode()).hexdigest() for key in keys]
        licenses: list[License] = []

        for key_hash in hashes:
            lic = repository.create(
                key_hash=key_hash,
                plan="basic",
                quota_monthly=100,
            )
            licenses.append(lic)

        # Simule du usage
        with SessionLocal() as session:
            for lic in licenses:
                license_model = session.get(LicenseModel, lic.id)
                if license_model:
                    license_model.used_this_month = 50
            session.commit()

        # Réinitialise
        repository.reset_monthly_usage()

        # Vérifie
        with SessionLocal() as session:
            for lic in licenses:
                license_model = session.get(LicenseModel, lic.id)
                assert license_model is not None
                assert license_model.used_this_month == 0

        # Cleanup
        with SessionLocal() as session:
            for lic in licenses:
                session.query(LicenseModel).filter(LicenseModel.id == lic.id).delete()
            session.commit()
