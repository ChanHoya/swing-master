"""
CORS 설정 테스트.

Starlette 의 allow_origins 는 정확한 문자열 비교다(is_allowed_origin 의
마지막 줄이 `return origin in self.allow_origins`). 그래서
"https://*.vercel.app" 같은 와일드카드는 에러도 내지 않고 조용히
아무것도 매칭하지 않는다. 배포한 뒤에야 CORS 차단으로 드러나므로
설정값 자체를 테스트로 묶어 둔다.
"""
import re

from app.core.config import settings


def test_allow_origins_contains_no_wildcard():
    """와일드카드는 조용히 실패한다. 정확한 오리진만 넣어야 한다."""
    for origin in settings.cors_origins:
        assert "*" not in origin, (
            f"{origin!r} 은 아무것도 매칭하지 않는다. "
            "패턴이 필요하면 CORS_ORIGIN_REGEX 를 쓸 것."
        )


def test_origin_regex_is_empty_by_default():
    """기본값은 닫혀 있어야 한다. 패턴은 배포 환경에서 명시적으로 준다."""
    assert settings.CORS_ORIGIN_REGEX == ""


def test_origin_regex_matches_only_the_intended_project():
    """프로젝트로 좁힌 패턴이 남의 vercel.app 을 통과시키면 안 된다."""
    pattern = r"https://swing-master-[a-z0-9-]+\.vercel\.app"
    assert re.fullmatch(pattern, "https://swing-master-abc123.vercel.app")
    assert not re.fullmatch(pattern, "https://evil.vercel.app")
    assert not re.fullmatch(pattern, "https://swing-master-abc.vercel.app.evil.com")


# ── 환경변수 파싱 — 배포를 세 번 깨뜨린 지점 ─────────────────────────────
#
# CORS_ORIGINS 를 List[str] 로 두면 pydantic-settings 가 환경변수를
# json.loads 로 먼저 해석하고, 실패하면 필드 검증기에 닿기도 전에
# SettingsError 를 던져 앱이 기동조차 못 한다. 대시보드에서 따옴표 하나만
# 어긋나도 그렇게 된다. 그래서 문자열로 받아 직접 파싱한다.
import pytest

from app.core.config import parse_origins


@pytest.mark.parametrize(
    "raw, expected",
    [
        # JSON 배열 — 문서와 render.yaml 이 안내하는 형식
        ('["https://a.vercel.app"]', ["https://a.vercel.app"]),
        ('["http://localhost:3000","https://a.vercel.app"]',
         ["http://localhost:3000", "https://a.vercel.app"]),
        # 쉼표 구분 — 사람이 대시보드에 손으로 넣기 가장 쉬운 형식
        ("http://localhost:3000,https://a.vercel.app",
         ["http://localhost:3000", "https://a.vercel.app"]),
        ("http://localhost:3000, https://a.vercel.app",
         ["http://localhost:3000", "https://a.vercel.app"]),
        # 값 하나
        ("https://a.vercel.app", ["https://a.vercel.app"]),
        # 망가진 JSON — 죽지 말고 건져낼 수 있는 만큼 건진다
        ('["https://a.vercel.app"', ["https://a.vercel.app"]),
        ("['https://a.vercel.app']", ["https://a.vercel.app"]),
        # 끝 슬래시 — 주소창에서 복사하면 따라온다. Origin 헤더에는
        # 경로가 없으므로 슬래시가 붙은 값은 무엇과도 매칭되지 않는다.
        ("https://a.vercel.app/", ["https://a.vercel.app"]),
        ('["https://a.vercel.app/"]', ["https://a.vercel.app"]),
        ("http://localhost:3000/,https://a.vercel.app/",
         ["http://localhost:3000", "https://a.vercel.app"]),
        # 빈 값
        ("", []),
        ("   ", []),
    ],
)
def test_parse_origins_accepts_both_formats(raw, expected):
    assert parse_origins(raw) == expected


def test_parse_origins_never_raises_on_garbage():
    """무엇이 들어와도 예외를 던지지 않는다. 기동 실패보다 빈 목록이 낫다."""
    for junk in ("{}", "[[[", '{"a": 1}', "null", ","):
        assert isinstance(parse_origins(junk), list)


def test_settings_exposes_parsed_list():
    from app.core.config import settings
    assert isinstance(settings.cors_origins, list)
    assert "http://localhost:3000" in settings.cors_origins
