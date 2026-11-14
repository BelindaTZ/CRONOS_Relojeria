"""Configuración central del backend.

Lee todo desde variables de entorno / `.env` (Constitución, Principio IX: secretos
solo vía `.env`, nunca hardcodeados). Si falta una variable obligatoria, la app
falla al arrancar con un mensaje claro en vez de un crash silencioso.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes de la aplicación validados al arranque."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- PostgreSQL ---
    database_url: str = Field(
        ...,
        description="URL SQLAlchemy, p. ej. postgresql+psycopg://user:pass@db:5432/cronos",
    )

    # --- MinIO ---
    minio_endpoint: str = Field(..., description="host:puerto del servicio MinIO (interno, contenedor)")
    minio_public_endpoint: str = Field(
        default="",
        description="host:puerto de MinIO accesible DESDE EL NAVEGADOR (p. ej. localhost:9100). "
        "Si queda vacío se usa `minio_endpoint`.",
    )
    minio_public_scheme: str = Field(default="http", description="http | https para las URLs públicas")
    minio_root_user: str = Field(...)
    minio_root_password: str = Field(...)
    minio_secure: bool = Field(default=False, description="usar TLS contra MinIO")

    # Buckets de cara a la app provisionados por la feature 000.
    # `landing-zone` NO se incluye: lo provisiona la feature 012.
    minio_public_buckets: tuple[str, ...] = ("reloj-imagenes", "perfil-usuarios")
    minio_private_buckets: tuple[str, ...] = ("comprobantes-venta", "documentos")

    # --- Auth / JWT ---
    jwt_secret: str = Field(..., description="clave de firma HS256 de los JWT de acceso")
    jwt_algorithm: str = Field(default="HS256")
    access_token_ttl_minutes: int = Field(default=30, description="vigencia del JWT de acceso")
    refresh_token_ttl_days: int = Field(default=14, description="vigencia del refresh token opaco")
    password_reset_ttl_hours: int = Field(default=24, description="caducidad de la contraseña temporal")

    # --- Rate limiting (login y restablecimiento) ---
    login_max_intentos: int = Field(default=5, description="intentos fallidos antes del bloqueo temporal")
    login_ventana_segundos: int = Field(default=300, description="ventana del contador de intentos")
    login_bloqueo_segundos: int = Field(default=900, description="duración del bloqueo temporal")

    # --- Correo ---
    email_backend: str = Field(default="console", description="console | smtp | sendgrid")
    email_from: str = Field(default="CRONOS <no-reply@cronos.local>")
    smtp_host: str = Field(default="localhost")
    smtp_port: int = Field(default=1025)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_tls: bool = Field(default=False)
    sendgrid_api_key: str = Field(default="")
    sendgrid_from_email: str = Field(
        default="", description="remitente verificado en SendGrid (Single Sender/dominio); si vacío usa email_from"
    )
    app_base_url: str = Field(default="http://localhost:5173", description="URL pública del frontend")

    # --- Semilla de Gerencia General (scripts/seed_gerencia) ---
    seed_gerencia_identificacion: str = Field(default="")
    seed_gerencia_nombre: str = Field(default="Gerencia General")
    seed_gerencia_email: str = Field(default="")
    seed_gerencia_password: str = Field(default="")

    # --- CORS ---
    cors_origins: str = Field(
        default="http://localhost:5173",
        description="orígenes permitidos, separados por coma",
    )

    # --- Arranque ---
    db_connect_timeout_seconds: int = Field(
        default=60,
        description="tiempo máximo de espera/reintento de PostgreSQL al arrancar",
    )

    app_version: str = Field(default="0.1.0")

    # --- feature 012: warehouse analítico (ClickHouse) + orquestador (Airflow) ---
    # El backend NUNCA abre estas conexiones al arrancar ni en /health (research
    # D7) — solo bajo demanda en /reportes/*, con degradación limpia si fallan.
    clickhouse_host: str = Field(default="clickhouse")
    clickhouse_http_port: int = Field(default=8123)
    clickhouse_user: str = Field(default="cronos")
    clickhouse_password: str = Field(default="")
    clickhouse_db: str = Field(default="wh")
    airflow_base_url: str = Field(default="http://airflow-webserver:8080")
    airflow_admin_user: str = Field(default="admin")
    airflow_admin_password: str = Field(default="")

    @property
    def minio_buckets(self) -> tuple[str, ...]:
        return self.minio_public_buckets + self.minio_private_buckets

    @property
    def minio_browser_endpoint(self) -> str:
        """Endpoint que sí resuelve el navegador. Fallback al interno."""
        return self.minio_public_endpoint.strip() or self.minio_endpoint

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Instancia única de `Settings` (cacheada)."""
    return Settings()
