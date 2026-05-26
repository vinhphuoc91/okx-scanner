"""Application settings loaded from environment variables.

All configuration is centralized here using ``pydantic-settings``.
Settings are immutable after construction and accessible via the
``settings`` singleton or :func:`get_settings` (cached).

Environment variables are loaded with the following precedence:
    1. Real process environment variables
    2. ``.env`` file in the project root (development convenience)
    3. Defaults defined on the model
"""

from __future__ import annotations

import os
from src.utils.compat import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


def normalize_database_url(url: str) -> str:
    """Normalize a PostgreSQL DSN for SQLAlchemy + psycopg v3.

    Accepts common schemes (``postgresql://``, ``postgres://``) and rewrites
    them to ``postgresql+psycopg://`` so we never fall back to psycopg2.
    """
    stripped = url.strip()
    if stripped.startswith("postgres://"):
        return "postgresql+psycopg://" + stripped.removeprefix("postgres://")
    if stripped.startswith("postgresql://"):
        return "postgresql+psycopg://" + stripped.removeprefix("postgresql://")
    return stripped


def read_database_url_from_environ() -> str | None:
    """Read ``DATABASE_URL`` directly from the process environment.

    Checked at runtime so shell overrides (``$env:DATABASE_URL=...``) always
    win over values loaded from ``.env`` during Settings construction.
    """
    raw = os.environ.get("DATABASE_URL")
    if raw and raw.strip():
        return raw.strip()
    return None


class AppEnv(StrEnum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Root application settings.

    Attributes
    ----------
    app_name : str
        Logical service name (appears in logs, metrics, alerts).
    app_env : AppEnv
        Deployment environment. Controls some defaults (e.g. SQL echo).
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
        # Process env vars override .env file values (pydantic-settings default).
        env_ignore_empty=True,
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_name: Annotated[str, Field(alias="APP_NAME")] = "okx-scanner"
    app_env: Annotated[AppEnv, Field(alias="APP_ENV")] = AppEnv.DEVELOPMENT
    app_debug: Annotated[bool, Field(alias="APP_DEBUG")] = False
    app_log_level: Annotated[LogLevel, Field(alias="APP_LOG_LEVEL")] = "INFO"
    app_timezone: Annotated[str, Field(alias="APP_TIMEZONE")] = "UTC"

    # -------------------------------------------------------------------------
    # API server
    # -------------------------------------------------------------------------
    api_host: Annotated[str, Field(alias="API_HOST")] = "0.0.0.0"  # noqa: S104
    api_port: Annotated[int, Field(alias="API_PORT", ge=1, le=65535)] = 8000
    api_workers: Annotated[int, Field(alias="API_WORKERS", ge=1, le=64)] = 4
    api_reload: Annotated[bool, Field(alias="API_RELOAD")] = False
    api_cors_origins: Annotated[str, Field(alias="API_CORS_ORIGINS")] = ""

    # -------------------------------------------------------------------------
    # PostgreSQL
    # -------------------------------------------------------------------------
    postgres_host: Annotated[str, Field(alias="POSTGRES_HOST")] = "postgres"
    postgres_port: Annotated[int, Field(alias="POSTGRES_PORT", ge=1, le=65535)] = 5432
    postgres_user: Annotated[str, Field(alias="POSTGRES_USER")] = "okx"
    postgres_password: Annotated[SecretStr, Field(alias="POSTGRES_PASSWORD")] = SecretStr("")
    postgres_db: Annotated[str, Field(alias="POSTGRES_DB")] = "okx_scanner"
    postgres_pool_size: Annotated[int, Field(alias="POSTGRES_POOL_SIZE", ge=1)] = 10
    postgres_max_overflow: Annotated[int, Field(alias="POSTGRES_MAX_OVERFLOW", ge=0)] = 20
    postgres_pool_timeout: Annotated[int, Field(alias="POSTGRES_POOL_TIMEOUT", ge=1)] = 30
    postgres_echo: Annotated[bool, Field(alias="POSTGRES_ECHO")] = False
    database_url_override: Annotated[str | None, Field(alias="DATABASE_URL")] = None

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    redis_host: Annotated[str, Field(alias="REDIS_HOST")] = "redis"
    redis_port: Annotated[int, Field(alias="REDIS_PORT", ge=1, le=65535)] = 6379
    redis_db: Annotated[int, Field(alias="REDIS_DB", ge=0, le=15)] = 0
    redis_password: Annotated[SecretStr, Field(alias="REDIS_PASSWORD")] = SecretStr("")
    redis_max_connections: Annotated[int, Field(alias="REDIS_MAX_CONNECTIONS", ge=1)] = 50
    redis_socket_timeout: Annotated[int, Field(alias="REDIS_SOCKET_TIMEOUT", ge=1)] = 5
    redis_url_override: Annotated[str | None, Field(alias="REDIS_URL")] = None

    # -------------------------------------------------------------------------
    # OKX API
    # -------------------------------------------------------------------------
    okx_api_key: Annotated[SecretStr, Field(alias="OKX_API_KEY")] = SecretStr("")
    okx_api_secret: Annotated[SecretStr, Field(alias="OKX_API_SECRET")] = SecretStr("")
    okx_api_passphrase: Annotated[SecretStr, Field(alias="OKX_API_PASSPHRASE")] = SecretStr("")
    okx_api_base_url: Annotated[str, Field(alias="OKX_API_BASE_URL")] = "https://www.okx.com"
    okx_ws_public_url: Annotated[str, Field(alias="OKX_WS_PUBLIC_URL")] = (
        "wss://ws.okx.com:8443/ws/v5/public"
    )
    okx_ws_private_url: Annotated[str, Field(alias="OKX_WS_PRIVATE_URL")] = (
        "wss://ws.okx.com:8443/ws/v5/private"
    )
    okx_use_testnet: Annotated[bool, Field(alias="OKX_USE_TESTNET")] = True

    # -------------------------------------------------------------------------
    # Scanner
    # -------------------------------------------------------------------------
    scanner_interval_seconds: Annotated[int, Field(alias="SCANNER_INTERVAL_SECONDS", ge=1)] = 60
    scanner_max_instruments: Annotated[int, Field(alias="SCANNER_MAX_INSTRUMENTS", ge=1)] = 200
    scanner_min_volume_24h_usd: Annotated[
        float, Field(alias="SCANNER_MIN_VOLUME_24H_USD", ge=0)
    ] = 1_000_000.0
    scanner_quote_currencies: Annotated[str, Field(alias="SCANNER_QUOTE_CURRENCIES")] = "USDT,USDC"

    # -------------------------------------------------------------------------
    # Market filter & tiering
    # -------------------------------------------------------------------------
    filter_min_volume_usd: Annotated[
        float, Field(alias="FILTER_MIN_VOLUME_USD", ge=0)
    ] = 1_000_000.0
    filter_max_spread_pct: Annotated[
        float, Field(alias="FILTER_MAX_SPREAD_PCT", ge=0)
    ] = 0.5
    filter_min_listing_age_days: Annotated[
        int, Field(alias="FILTER_MIN_LISTING_AGE_DAYS", ge=0)
    ] = 7
    filter_quote_currencies: Annotated[str, Field(alias="FILTER_QUOTE_CURRENCIES")] = "USDT"
    filter_inst_types: Annotated[str, Field(alias="FILTER_INST_TYPES")] = "SPOT,SWAP"
    filter_tier1_size: Annotated[int, Field(alias="FILTER_TIER1_SIZE", ge=1)] = 50
    filter_tier2_size: Annotated[int, Field(alias="FILTER_TIER2_SIZE", ge=1)] = 200
    filter_tier1_interval_seconds: Annotated[
        int, Field(alias="FILTER_TIER1_INTERVAL_SECONDS", ge=1)
    ] = 60
    filter_tier2_interval_seconds: Annotated[
        int, Field(alias="FILTER_TIER2_INTERVAL_SECONDS", ge=1)
    ] = 300
    filter_tier3_interval_seconds: Annotated[
        int, Field(alias="FILTER_TIER3_INTERVAL_SECONDS", ge=1)
    ] = 900

    # -------------------------------------------------------------------------
    # Strategy engine
    # -------------------------------------------------------------------------
    funding_rate_long_threshold: Annotated[
        float, Field(alias="FUNDING_RATE_LONG_THRESHOLD")
    ] = -0.0002
    funding_rate_short_threshold: Annotated[
        float, Field(alias="FUNDING_RATE_SHORT_THRESHOLD")
    ] = 0.0005
    momentum_ema_fast: Annotated[int, Field(alias="MOMENTUM_EMA_FAST", ge=1)] = 20
    momentum_ema_slow: Annotated[int, Field(alias="MOMENTUM_EMA_SLOW", ge=1)] = 50
    momentum_rsi_period: Annotated[int, Field(alias="MOMENTUM_RSI_PERIOD", ge=1)] = 14
    momentum_rsi_bull: Annotated[float, Field(alias="MOMENTUM_RSI_BULL", ge=0, le=100)] = 55.0
    momentum_rsi_bear: Annotated[float, Field(alias="MOMENTUM_RSI_BEAR", ge=0, le=100)] = 45.0
    momentum_volume_multiplier: Annotated[
        float, Field(alias="MOMENTUM_VOLUME_MULTIPLIER", ge=0)
    ] = 1.5
    momentum_min_volume_24h_usd: Annotated[
        float, Field(alias="MOMENTUM_MIN_VOLUME_24H_USD", ge=0)
    ] = 5_000_000.0  # Filter micro-cap: only trade coins with 24h volume >= $5M

    # Breakout
    breakout_consolidation_candles: Annotated[
        int, Field(alias="BREAKOUT_CONSOLIDATION_CANDLES", ge=2)
    ] = 10
    breakout_range_max_pct: Annotated[
        float, Field(alias="BREAKOUT_RANGE_MAX_PCT", ge=0)
    ] = 2.0
    breakout_volume_multiplier: Annotated[
        float, Field(alias="BREAKOUT_VOLUME_MULTIPLIER", ge=0)
    ] = 2.0
    breakout_threshold_pct: Annotated[
        float, Field(alias="BREAKOUT_THRESHOLD_PCT", ge=0)
    ] = 0.5

    # Volume anomaly
    volume_anomaly_multiplier: Annotated[
        float, Field(alias="VOLUME_ANOMALY_MULTIPLIER", ge=0)
    ] = 2.5  # Giảm từ 4.0 → dễ trigger hơn
    volume_anomaly_max_price_change: Annotated[
        float, Field(alias="VOLUME_ANOMALY_MAX_PRICE_CHANGE", ge=0)
    ] = 3.0  # Tăng từ 1.5% → cho phép price move nhiều hơn

    # Trend pullback
    trend_pullback_ema_fast: Annotated[
        int, Field(alias="TREND_PULLBACK_EMA_FAST", ge=1)
    ] = 20
    trend_pullback_ema_slow: Annotated[
        int, Field(alias="TREND_PULLBACK_EMA_SLOW", ge=1)
    ] = 50
    trend_pullback_tolerance_pct: Annotated[
        float, Field(alias="TREND_PULLBACK_TOLERANCE_PCT", ge=0)
    ] = 0.5
    trend_pullback_min_angle: Annotated[
        float, Field(alias="TREND_PULLBACK_MIN_ANGLE", ge=0)
    ] = 0.1

    # Correlation divergence
    correlation_min_divergence: Annotated[
        float, Field(alias="CORRELATION_MIN_DIVERGENCE", ge=0)
    ] = 1.5
    correlation_strong_divergence: Annotated[
        float, Field(alias="CORRELATION_STRONG_DIVERGENCE", ge=0)
    ] = 2.5
    correlation_timeframe: Annotated[str, Field(alias="CORRELATION_TIMEFRAME")] = "1H"
    correlation_min_tier: Annotated[int, Field(alias="CORRELATION_MIN_TIER", ge=1, le=3)] = 2

    # Liquidation zone
    liq_min_oi_change: Annotated[float, Field(alias="LIQ_MIN_OI_CHANGE", ge=0)] = 8.0  # Giảm từ 20% → dễ trigger hơn
    liq_funding_extreme_high: Annotated[
        float, Field(alias="LIQ_FUNDING_EXTREME_HIGH")
    ] = 0.0005
    liq_funding_extreme_low: Annotated[
        float, Field(alias="LIQ_FUNDING_EXTREME_LOW")
    ] = -0.0002
    liq_rsi_overbought: Annotated[
        float, Field(alias="LIQ_RSI_OVERBOUGHT", ge=0, le=100)
    ] = 70.0
    liq_rsi_oversold: Annotated[
        float, Field(alias="LIQ_RSI_OVERSOLD", ge=0, le=100)
    ] = 30.0
    liq_score_penalty: Annotated[
        float, Field(alias="LIQ_SCORE_PENALTY", ge=0)
    ] = 10.0

    # Statistical arbitrage
    stat_arb_min_basis: Annotated[float, Field(alias="STAT_ARB_MIN_BASIS", ge=0)] = 0.2
    stat_arb_strong_basis: Annotated[float, Field(alias="STAT_ARB_STRONG_BASIS", ge=0)] = 0.5
    stat_arb_basis_trend_periods: Annotated[
        int, Field(alias="STAT_ARB_BASIS_TREND_PERIODS", ge=2)
    ] = 5

    # -------------------------------------------------------------------------
    # Scoring & risk
    # -------------------------------------------------------------------------
    scoring_min_threshold: Annotated[
        int, Field(alias="SCORING_MIN_THRESHOLD", ge=0, le=100)
    ] = 70
    scoring_grade_excellent: Annotated[
        int, Field(alias="SCORING_GRADE_EXCELLENT", ge=0, le=100)
    ] = 85
    scoring_grade_good: Annotated[
        int, Field(alias="SCORING_GRADE_GOOD", ge=0, le=100)
    ] = 75
    scoring_grade_watch: Annotated[
        int, Field(alias="SCORING_GRADE_WATCH", ge=0, le=100)
    ] = 65
    scoring_model_version: Annotated[str, Field(alias="SCORING_MODEL_VERSION")] = "v1"
    alert_min_score: Annotated[int, Field(alias="ALERT_MIN_SCORE", ge=0, le=100)] = 65
    risk_max_spread_pct: Annotated[float, Field(alias="RISK_MAX_SPREAD_PCT", ge=0)] = 0.3
    risk_min_volume_usd: Annotated[float, Field(alias="RISK_MIN_VOLUME_USD", ge=0)] = 500_000.0
    risk_extreme_funding_rate: Annotated[
        float, Field(alias="RISK_EXTREME_FUNDING_RATE", ge=0)
    ] = 0.003
    risk_max_position_usd: Annotated[float, Field(alias="RISK_MAX_POSITION_USD", ge=0)] = 1000.0
    risk_max_daily_loss_usd: Annotated[float, Field(alias="RISK_MAX_DAILY_LOSS_USD", ge=0)] = 500.0
    risk_max_concurrent_positions: Annotated[
        int, Field(alias="RISK_MAX_CONCURRENT_POSITIONS", ge=0)
    ] = 5

    # -------------------------------------------------------------------------
    # Alerting
    # -------------------------------------------------------------------------
    alert_enabled: Annotated[bool, Field(alias="ALERT_ENABLED")] = True
    alert_cooldown_seconds: Annotated[int, Field(alias="ALERT_COOLDOWN_SECONDS", ge=0)] = 300
    alert_telegram_bot_token: Annotated[
        SecretStr, Field(alias="ALERT_TELEGRAM_BOT_TOKEN")
    ] = SecretStr("")
    alert_telegram_chat_id: Annotated[str, Field(alias="ALERT_TELEGRAM_CHAT_ID")] = ""
    alert_webhook_url: Annotated[str, Field(alias="ALERT_WEBHOOK_URL")] = ""

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------
    sentry_dsn: Annotated[SecretStr, Field(alias="SENTRY_DSN")] = SecretStr("")
    prometheus_enabled: Annotated[bool, Field(alias="PROMETHEUS_ENABLED")] = True
    prometheus_port: Annotated[int, Field(alias="PROMETHEUS_PORT", ge=1, le=65535)] = 9090

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator(
        "api_cors_origins",
        "scanner_quote_currencies",
        "filter_quote_currencies",
        "filter_inst_types",
    )
    @classmethod
    def _strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    # -------------------------------------------------------------------------
    # Computed properties
    # -------------------------------------------------------------------------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        """True when running in the production environment."""
        return self.app_env == AppEnv.PRODUCTION

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        """True when running in the development environment."""
        return self.app_env == AppEnv.DEVELOPMENT

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Synchronous PostgreSQL DSN for SQLAlchemy.

        Resolution order (first match wins):

        1. ``DATABASE_URL`` in ``os.environ`` (runtime shell override)
        2. ``DATABASE_URL`` loaded via pydantic-settings (env + .env file)
        3. Individual ``POSTGRES_*`` component fields

        Always normalized to ``postgresql+psycopg://`` for the psycopg v3 driver.
        """
        env_url = read_database_url_from_environ()
        if env_url:
            return normalize_database_url(env_url)
        if self.database_url_override:
            return normalize_database_url(self.database_url_override)
        dsn = PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value() or None,
            host=self.postgres_host,
            port=self.postgres_port,
            path=self.postgres_db,
        )
        return str(dsn)

    @property
    def DATABASE_URL(self) -> str:  # noqa: N802 — matches env-var naming convention
        """Alias for :attr:`database_url` (used by DB session / Alembic)."""
        return self.database_url

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_source(self) -> str:
        """Indicate which configuration path supplied the active DSN."""
        if read_database_url_from_environ():
            return "DATABASE_URL (os.environ)"
        if self.database_url_override:
            return "DATABASE_URL (settings)"
        return "POSTGRES_* components"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        """Redis DSN for the ``redis-py`` client."""
        if self.redis_url_override:
            return self.redis_url_override
        password = self.redis_password.get_secret_value()
        dsn = RedisDsn.build(
            scheme="redis",
            password=password or None,
            host=self.redis_host,
            port=self.redis_port,
            path=str(self.redis_db),
        )
        return str(dsn)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        """Parsed list of CORS allow-origins."""
        if not self.api_cors_origins:
            return []
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def quote_currency_list(self) -> list[str]:
        """Parsed list of quote currencies to scan."""
        return [
            c.strip().upper()
            for c in self.scanner_quote_currencies.split(",")
            if c.strip()
        ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def filter_quote_currency_list(self) -> list[str]:
        """Quote currencies accepted by the market filter."""
        return [
            c.strip().upper()
            for c in self.filter_quote_currencies.split(",")
            if c.strip()
        ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def filter_inst_type_list(self) -> list[str]:
        """Instrument types accepted by the market filter."""
        return [
            t.strip().upper()
            for t in self.filter_inst_types.split(",")
            if t.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings singleton.

    The cache ensures we instantiate :class:`Settings` exactly once per
    process — useful for FastAPI dependency injection and to avoid repeated
    .env parsing.
    """
    return Settings()


# Module-level singleton for convenience imports
settings: Settings = get_settings()
