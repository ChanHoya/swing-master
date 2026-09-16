"""
Top-level API router — aggregates all sub-routers.
"""
from fastapi import APIRouter

from app.api.endpoints import health, upload, analysis, auth, history

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(history.router, tags=["History"])
