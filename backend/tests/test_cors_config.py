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
    for origin in settings.CORS_ORIGINS:
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
