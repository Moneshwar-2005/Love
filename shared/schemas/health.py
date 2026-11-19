"""
Health check schema models.
"""

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field

from shared.constants import DatabaseStatus, ServiceStatus


class ServiceHealthDetail(BaseModel):
    """Status details for an individual subsystem or external dependency."""
    status: ServiceStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None


class HealthCheckResponse(BaseModel):
    """Standardized health check payload returned by the health endpoint."""
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Semantic application version")
    status: ServiceStatus = Field(..., description="Overall service status")
    environment: str = Field(..., description="Active runtime environment")
    database_status: DatabaseStatus = Field(..., description="Database connectivity state")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current UTC timestamp")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    services: Dict[str, ServiceHealthDetail] = Field(
        default_factory=dict,
        description="Detailed status breakdown per subsystem"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "app_name": "LOVE Personal AI Assistant",
                "version": "0.1.0",
                "status": "healthy",
                "environment": "development",
                "database_status": "connected",
                "timestamp": "2026-11-19T10:45:00.000000Z",
                "uptime_seconds": 124.5,
                "services": {
                    "database": {
                        "status": "healthy",
                        "message": "SQLite async connection verified",
                        "latency_ms": 1.2
                    }
                }
            }
        }
    }
