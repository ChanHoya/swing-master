"""
기동 시 설정 점검 테스트.

운영에서 DATABASE_URL 을 빠뜨리면 앱은 config.py 의 기본값(localhost)으로
조용히 떨어져 컨테이너 자기 자신에게 접속하고, 화면에는 원인과 무관해
보이는 ConnectionRefusedError 가 찍힌다. 실제 Render 배포가 그렇게
실패했다. 설정 실수는 설정 실수라고 말해야 한다.
"""
import pytest

from app.core.config import settings
from app.main import check_production_config


def test_passes_with_a_remote_database(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(
        settings, "DATABASE_URL",
        "postgresql+asyncpg://u:p@ep-x.ap-southeast-1.aws.neon.tech/neondb",
    )
    check_production_config()  # 예외가 없으면 통과


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://postgres:postgres@localhost:5432/swingmaster",
        "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/swingmaster",
    ],
)
def test_rejects_localhost_in_production(monkeypatch, url):
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    with pytest.raises(RuntimeError) as exc:
        check_production_config()
    assert "DATABASE_URL" in str(exc.value)


def test_allows_localhost_in_development(monkeypatch):
    """로컬 개발은 당연히 localhost 를 쓴다. 막으면 안 된다."""
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(
        settings, "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/swingmaster",
    )
    check_production_config()


def test_rejects_default_secret_key_in_production(monkeypatch):
    """서명 키가 기본값이면 누구나 토큰을 위조할 수 있다."""
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(
        settings, "DATABASE_URL",
        "postgresql+asyncpg://u:p@ep-x.neon.tech/neondb",
    )
    monkeypatch.setattr(settings, "SECRET_KEY", "change-me-in-production")
    with pytest.raises(RuntimeError) as exc:
        check_production_config()
    assert "SECRET_KEY" in str(exc.value)
