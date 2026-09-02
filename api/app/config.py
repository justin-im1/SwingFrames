from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://swingframes:swingframes@localhost:5432/swingframes"
    )
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001"
    )
    max_upload_bytes: int = 500 * 1024 * 1024
    max_duration_s: float = 60.0
    storage_dir: str = str(ROOT / "storage")
    distinct_frame_warn_ratio: float = 0.5

    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("+asyncpg", "+psycopg2")

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_dir)


settings = Settings()
