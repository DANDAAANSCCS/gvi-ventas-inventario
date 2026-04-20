from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracion leida de variables de entorno (.env)."""

    database_url: str = "postgresql+asyncpg://gvi:gvi_pass@localhost:5432/gvi"
    jwt_secret: str = "cambia-esto"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:8080"
    admin_email: str = "admin@gvi.com"
    admin_password: str = "Admin123!"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
