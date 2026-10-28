"""Ortam değişkenlerinden yapılandırma. Gizli anahtarlar yalnızca burada okunur, asla loglanmaz."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name)
    return val if val not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", "sqlite:///./bilanco.db"))
    redis_url: str | None = field(default_factory=lambda: _env("REDIS_URL"))
    http_timeout: float = field(default_factory=lambda: float(_env("HTTP_TIMEOUT_SECONDS", "60")))
    http_max_retries: int = field(default_factory=lambda: int(_env("HTTP_MAX_RETRIES", "3")))
    user_agent: str = field(default_factory=lambda: _env("HTTP_USER_AGENT", "BilancoBot/0.1 (veri toplama)"))
    raw_store_dir: Path = field(default_factory=lambda: Path(_env("RAW_STORE_DIR", "./data/raw")))
    min_seconds_between_requests: float = field(default_factory=lambda: float(_env("MIN_SECONDS_BETWEEN_REQUESTS", "2")))
    scheduler_enabled: bool = field(default_factory=lambda: _env("SCHEDULER_ENABLED", "false").lower() == "true")
    # robots.txt politikası: strict = yasaklı yol indirilmez (varsayılan); lenient = uyarı logla, yalnızca açıkça yapılandırılmış
    # resmî istatistik dosyaları için düşük hızda devam et (tarama yapılmaz). Karar kullanıcıya aittir (docs/sources.md).
    robots_policy: str = field(default_factory=lambda: _env("ROBOTS_POLICY", "strict").lower())
    scheduler_timezone: str = field(default_factory=lambda: _env("SCHEDULER_TIMEZONE", "Europe/Istanbul"))

    @property
    def evds_api_key(self) -> str | None:
        """Her çağrıda ortamdan okunur; nesnede saklanmaz, repr'da görünmez."""
        return _env("EVDS_API_KEY")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()
