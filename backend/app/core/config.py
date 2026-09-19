"""
Application Configuration — Pydantic Settings
Reads from environment variables (or .env file)
"""
import json
from functools import lru_cache
from typing import List


def _normalise(origin: str) -> str:
    """오리진 하나를 다듬는다.

    끝의 슬래시를 뗀다. 브라우저의 Origin 헤더는 스킴+호스트+포트만 담고
    경로가 없으므로, 슬래시가 붙은 값은 무엇과도 매칭되지 않는다. 주소창에서
    복사하면 슬래시가 따라오기 때문에 실제로 배포가 이것 때문에 막혔다.
    """
    return origin.strip().strip("\"'[] ").rstrip("/")


def parse_origins(raw: str) -> List[str]:
    """CORS 오리진 문자열을 리스트로. JSON 배열과 쉼표 구분을 모두 받는다.

    환경변수 이름을 List[str] 로 선언하면 pydantic-settings 가 값을
    json.loads 로 먼저 해석하고, 실패하면 필드 검증기에 닿기도 전에
    SettingsError 를 던진다. 대시보드에서 따옴표 하나만 어긋나도 앱이
    기동조차 못 하고 죽는다. 실제로 Render 배포가 그렇게 실패했다.

    그래서 문자열로 받아 여기서 직접 판다. 무엇이 들어와도 예외를 던지지
    않는다 — 기동 실패보다 빈 목록이 낫다.
    """
    raw = (raw or "").strip()
    if not raw:
        return []

    if raw.startswith("["):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            pass  # 아래 쉼표 분리로 건져 본다
        else:
            if isinstance(value, list):
                return [_normalise(str(v)) for v in value if _normalise(str(v))]
            return []

    cleaned = (_normalise(p) for p in raw.split(","))
    return [p for p in cleaned if p]

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
    # 문자열로 받는다 — 위 parse_origins 의 설명 참고. 읽을 때는
    # settings.cors_origins 를 쓴다.
    # JSON 배열 ["https://a.app","https://b.app"] 과
    # 쉼표 구분  https://a.app,https://b.app  을 모두 받는다.
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://MacBook-Air.local:3000"
    )

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

    @property
    def cors_origins(self) -> List[str]:
        """CORSMiddleware 에 넘길 오리진 목록."""
        return parse_origins(self.CORS_ORIGINS)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
