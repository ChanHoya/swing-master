"""
Application Configuration — Pydantic Settings
Reads from environment variables (or .env file)
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────────────────
    ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ── CORS ─────────────────────────────────────────────────────────────────
    # 같은 와이파이의 폰에서 접속하려면 맥의 LAN 주소도 허용해야 한다.
    # .local 이름은 IP 가 바뀌어도 그대로라 고정 주소로 쓸 수 있다.
    # 다른 기기나 IP 를 쓸 때는 CORS_ORIGINS 환경변수로 덮어쓴다.
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://MacBook-Air.local:3000",
        "https://*.vercel.app",
    ]

    # ── Database (Supabase PostgreSQL) ───────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/swingmaster"

    # ── Cloudflare R2 / AWS S3 ───────────────────────────────────────────────
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "swing-master"
    R2_PUBLIC_URL: str = ""  # Custom domain or R2 public URL

    # ── LLM APIs ─────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_API_KEY: str = ""

    # ── Rate Limiting ────────────────────────────────────────────────────────
    ANON_DAILY_LIMIT: int = 1
    AUTH_DAILY_LIMIT: int = 5

    # ── Sentry ───────────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
