"""Persistence adapters and database setup."""

from app.infrastructure.persistence.database import create_schema

__all__ = ["create_schema"]
