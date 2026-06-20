"""API v1 router aggregation."""
from fastapi import APIRouter

from .auth import router as auth_router
from .lectures import router as lectures_router
from .capture import router as capture_router
from .audit import router as audit_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(lectures_router)
api_router.include_router(capture_router)
api_router.include_router(audit_router)
