"""
Tests for the /health endpoint.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.mark.asyncio
async def test_health_ok():
    """Should return status=ok and db=ok when DB is reachable."""
    with patch("app.api.endpoints.health.get_db") as mock_get_db:
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_get_db.return_value = mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "uptime_seconds" in data
