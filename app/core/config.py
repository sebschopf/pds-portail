from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/app.db"
    ckan_base_url: str = "https://opendata.swiss"
    cors_allowed_origins: str = "http://localhost:5173"
    cors_allowed_origin_regex: str | None = None
    enable_ckan_sync: bool = False
    ckan_sync_bootstrap_if_empty: bool = True
    ckan_sync_interval_minutes: int = 60
    ckan_sync_batch_rows: int = 100
    ckan_sync_max_batches_per_run: int = 10
    ckan_sync_batch_delay_seconds: float = 1.0
    ckan_http_timeout_seconds: float = 30.0
    expose_api_docs: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def parsed_cors_allowed_origins(self) -> list[str]:
        """Retourne des origines CORS nettoyees et dedupliquees.

        Exemple attendu en variable d'env:
        CORS_ALLOWED_ORIGINS="https://pds-portail.vercel.app, http://localhost:5173"
        """

        seen: set[str] = set()
        origins: list[str] = []
        for raw_origin in self.cors_allowed_origins.split(","):
            origin = raw_origin.strip().rstrip("/")
            if not origin or origin in seen:
                continue
            seen.add(origin)
            origins.append(origin)
        return origins


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
