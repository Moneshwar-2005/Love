"""
Aggregated v1 API routing.
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import auth, devices, health

api_v1_router = APIRouter(prefix="/v1")

# Include v1 endpoints
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(devices.router)
