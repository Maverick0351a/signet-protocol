import json
import os

from pydantic import BaseModel


def _getenv(*names, default=None):
    for n in names:
        val = os.getenv(n)
        if val not in (None, ""):
            return val
    return default


class TenantConfig(BaseModel):
    tenant: str
    free_quota: int = 5000
    allowlist: list[str] = []
    stripe_item_vex: str | None = None
    stripe_item_fu: str | None = None
    fallback_enabled: bool = False
    fu_monthly_limit: int | None = None  # FU quota limit per month


class Settings(BaseModel):
    api_keys: dict[str, TenantConfig]
    hel_allowlist: list[str]
    db_path: str
    receipts_jsonl: str | None = None
    private_key_b64: str | None = None
    kid: str | None = None
    stripe_api_key: str | None = None
    openai_api_key: str | None = None
    port: int = int(_getenv("PORT", default="8088"))

    # Storage configuration
    storage_type: str = "sqlite"  # "sqlite" or "postgres"
    postgres_url: str | None = None

    # Reserved capacity configuration
    reserved_config_path: str | None = None


def load_settings() -> Settings:
    raw = _getenv("SP_API_KEYS", "AB_API_KEYS", default="{}")
    try:
        mapping = json.loads(raw)
    except Exception:
        mapping = {}
    api_keys = {}
    for k, v in mapping.items():
        api_keys[k] = TenantConfig(**v)

    hel = _getenv("SP_HEL_ALLOWLIST", "AB_HEL_ALLOWLIST", default="")
    hel_allowlist = [h.strip() for h in hel.split(",") if h.strip()]

    # Determine storage type
    storage_type = _getenv("SP_STORAGE", default="sqlite").lower()

    # Database configuration based on storage type
    if storage_type == "postgres":
        db_path = _getenv("SP_POSTGRES_URL", "DATABASE_URL", default="")
        if not db_path:
            print("Warning: PostgreSQL storage selected but no connection string provided")
            storage_type = "sqlite"
            db_path = _getenv("SP_DB_PATH", "AB_DB_PATH", default="./data/signet.db")
    else:
        db_path = _getenv("SP_DB_PATH", "AB_DB_PATH", default="./data/signet.db")

    settings = Settings(
        api_keys=api_keys,
        hel_allowlist=hel_allowlist,
        db_path=db_path,
        receipts_jsonl=_getenv("SP_RECEIPTS_JSONL", "AB_RECEIPTS_JSONL"),
        private_key_b64=_getenv("SP_PRIVATE_KEY_B64", "AB_PRIVATE_KEY_B64"),
        kid=_getenv("SP_KID", "AB_KID"),
        stripe_api_key=_getenv("SP_STRIPE_API_KEY", "STRIPE_API_KEY"),
        openai_api_key=_getenv("SP_OPENAI_API_KEY", "OPENAI_API_KEY"),
        storage_type=storage_type,
        postgres_url=db_path if storage_type == "postgres" else None,
        reserved_config_path=_getenv("SP_RESERVED_CONFIG", default="./reserved.json"),
    )
    return settings


def create_storage_from_settings(settings: Settings):
    """Factory function to create appropriate storage backend"""
    if settings.storage_type == "postgres":
        from .pipeline.storage_postgres import PostgreSQLStorage

        return PostgreSQLStorage(settings.postgres_url)
    else:
        from .pipeline.storage import Storage

        return Storage(settings.db_path)
