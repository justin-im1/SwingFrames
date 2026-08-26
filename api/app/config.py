from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://swingframes:swingframes@localhost:5432/swingframes"
    )
    cors_origins: str = "http://localhost:3000"
    min_fps: float = 60.0
    warn_fps: float = 120.0
    max_duration_s: float = 15.0
    max_long_side: int = 1080
    resample_hz: float = 240.0
    max_upload_bytes: int = 500 * 1024 * 1024

    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("+asyncpg", "+psycopg2")

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]


settings = Settings()
