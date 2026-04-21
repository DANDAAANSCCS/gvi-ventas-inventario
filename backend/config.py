from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracion leida de variables de entorno (.env)."""

    database_url: str = "postgresql+asyncpg://gvi:gvi_pass@localhost:5432/gvi"
    jwt_secret: str = "cambia-esto"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    cors_origins: str = (
        "http://localhost:8080,"
        "http://localhost:8180,"
        "http://localhost:8181,"
        "http://localhost:8182,"
        "https://gvi.namu-li.com,"
        "https://admin.gvi.namu-li.com,"
        "https://db.gvi.namu-li.com"
    )
    admin_email: str = "admin@gvi.com"
    admin_password: str = "Admin123!"

    # URL publica del frontend (usada para armar el link del email de reset).
    frontend_url: str = "http://localhost:8180"

    # SMTP para envio de correos (recuperacion de contrasena).
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_from_name: str = "GesVentas"

    # Vigencia del token de reset (minutos).
    reset_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)


settings = Settings()
