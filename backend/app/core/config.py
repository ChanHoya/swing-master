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
    #
    # 여기에는 정확한 오리진만 넣는다. Starlette 은 문자열을 그대로 비교하므로
    # ("return origin in self.allow_origins") "https://*.vercel.app" 같은
    # 와일드카드는 에러 없이 조용히 아무것도 매칭하지 않는다.
    # 패턴이 필요하면 아래 CORS_ORIGIN_REGEX 를 쓴다.
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://MacBook-Air.local:3000",
    ]

    # Vercel 프리뷰처럼 주소가 매번 바뀌는 경우에만 쓴다. 전부 여는 대신
    # 프로젝트로 좁힌 패턴을 넣는다.
    # 예: https://swing-master-[a-z0-9-]+\.vercel\.app
    CORS_ORIGIN_REGEX: str = ""

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

    # ── 가입 잠금 ────────────────────────────────────────────────────────────
    # 공개 URL 에 올리면 누구나 가입할 수 있다. 초대 코드를 아는 사람만 받는다.
    # 비어 있으면 가입이 '열리는' 게 아니라 '닫힌다'. 환경변수를 깜빡하고
    # 배포했을 때 문이 열려 있으면 안 되기 때문이다.
    INVITE_CODE: str = ""

    # ── Rate Limiting ────────────────────────────────────────────────────────
    # 주의: 아래 두 값은 선언만 돼 있고 어디에서도 강제되지 않는다(미구현).
    # 가입이 INVITE_CODE 로 잠겨 있어 당장은 필요하지 않다.
    ANON_DAILY_LIMIT: int = 1
    AUTH_DAILY_LIMIT: int = 5

    # ── Sentry ───────────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
