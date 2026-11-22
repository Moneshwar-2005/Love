"""
Aggregated v1 API routing.
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import auth, devices, health, intelligence, memory, sync, system, voice, work

api_v1_router = APIRouter(prefix="/v1")

# Include v1 endpoints
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(devices.router)
api_v1_router.include_router(intelligence.router)
api_v1_router.include_router(memory.router)
api_v1_router.include_router(work.router)
api_v1_router.include_router(voice.router)
api_v1_router.include_router(system.router)
api_v1_router.include_router(sync.router)
