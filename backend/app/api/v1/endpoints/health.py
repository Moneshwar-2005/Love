"""
Health-check API endpoint.
Returns application name, version, runtime status, and subsystem health.
"""

import time
from datetime import datetime, timezone
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from backend.app.config.settings import get_settings
from backend.app.database.session import check_database_connection
from shared.constants import DatabaseStatus, ServiceStatus
from shared.schemas.health import HealthCheckResponse, ServiceHealthDetail

router = APIRouter(tags=["Health"])
settings = get_settings()

# Process start time for uptime calculation
_START_TIME = time.perf_counter()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    description="Returns current service status, version, uptime, and database connectivity."
)
async def get_health() -> HealthCheckResponse:
    """
    Evaluate system health and return status.
    If core services are failing, returns 503 Service Unavailable.
    """
    uptime = round(time.perf_counter() - _START_TIME, 2)
    db_status, db_detail = await check_database_connection()

    overall_status = ServiceStatus.HEALTHY
    http_status = status.HTTP_200_OK

    if db_status != DatabaseStatus.CONNECTED:
        overall_status = ServiceStatus.DEGRADED
        # Can still respond 200 or 503 depending on criticality; for health check we report degraded

    response_payload = HealthCheckResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        status=overall_status,
        environment=settings.APP_ENV,
        database_status=db_status,
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=uptime,
        services={
            "database": ServiceHealthDetail(
                status=db_detail.get("status", ServiceStatus.UNHEALTHY),
                message=db_detail.get("message"),
                latency_ms=db_detail.get("latency_ms"),
            )
        }
    )

    if overall_status == ServiceStatus.UNHEALTHY:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=response_payload.model_dump(mode="json"))

    return response_payload
