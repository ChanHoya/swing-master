"""
Health check endpoint — GET /health
"""
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()

_START_TIME = time.time()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Service health check.

    Returns:
        - status: "ok" | "degraded"
        - db: "ok" | "error"
        - uptime_seconds: float
    """
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "version": "0.1.0",
    }
