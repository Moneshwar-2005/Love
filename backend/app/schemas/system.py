"""
Pydantic schemas for System Observability and Hardware Metrics (Phase 08).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RamMetrics(BaseModel):
    """Authoritative RAM usage measurements."""
    used_gb: float = Field(..., description="Used RAM in gigabytes")
    total_gb: float = Field(..., description="Total system RAM in gigabytes")
    percent: float = Field(..., description="RAM utilization percentage")


class GpuMetrics(BaseModel):
    """Authoritative GPU and VRAM hardware measurements."""
    available: bool = Field(..., description="Whether a dedicated GPU is detected")
    name: str = Field(..., description="GPU model designation")
    vram_used_gb: Optional[float] = Field(None, description="Used VRAM in gigabytes")
    vram_total_gb: Optional[float] = Field(None, description="Total VRAM in gigabytes")
    vram_percent: Optional[float] = Field(None, description="VRAM utilization percentage")
    utilization_percent: Optional[float] = Field(None, description="GPU core utilization percentage")


class LocalModelStatus(BaseModel):
    """Status and health of local inference backend (Ollama)."""
    is_running: bool = Field(..., description="Whether local service is responsive")
    service_name: str = Field(default="ollama", description="Local runtime designation")
    latency_ms: Optional[float] = Field(None, description="Ping roundtrip latency in ms")
    error: Optional[str] = Field(None, description="Connection error message if unavailable")


class SystemMetricsResponse(BaseModel):
    """Authoritative real-time system resource metrics."""
    cpu_percent: float = Field(..., description="Current instantaneous CPU usage percentage")
    ram: RamMetrics = Field(..., description="System memory allocation")
    gpu: GpuMetrics = Field(..., description="GPU and VRAM hardware metrics")
    local_model: LocalModelStatus = Field(..., description="Local AI model service status")
    uptime_seconds: float = Field(..., description="Backend process uptime in seconds")
    timestamp: datetime = Field(..., description="UTC measurement timestamp")


class SystemActivityItem(BaseModel):
    """Individual event in the unified system activity timeline."""
    id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event classification (e.g. conversation_created, task_completed)")
    title: str = Field(..., description="Human-readable event headline")
    description: Optional[str] = Field(None, description="Descriptive event details")
    category: str = Field(..., description="Domain category: intelligence, work, memory, voice, security")
    timestamp: datetime = Field(..., description="UTC event timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual event payload")


class SystemActivityResponse(BaseModel):
    """Unified system activity timeline response."""
    items: List[SystemActivityItem] = Field(..., description="Chronological activity items")
    total: int = Field(..., description="Total items returned in window")


class LastBackupDetail(BaseModel):
    """Metadata regarding the most recent verified backup."""
    filename: str
    created_at: str
    size_bytes: int
    is_valid: bool
    total_backups: int


class DatabaseHealthResponse(BaseModel):
    """Authoritative database health and diagnostic operational metrics."""
    engine: str = Field(..., description="Database engine dialect: sqlite, postgresql")
    status: str = Field(..., description="Connection status: connected, error")
    latency_ms: float = Field(..., description="Query turnaround latency in ms")
    is_sqlite: bool = Field(..., description="Whether operating on local standalone SQLite")
    is_postgresql: bool = Field(..., description="Whether operating on client-server PostgreSQL")
    journal_mode: Optional[str] = Field(None, description="SQLite journal mode: WAL, delete")
    foreign_keys_enabled: bool = Field(..., description="Whether foreign key integrity constraints are actively enforced")
    integrity_status: str = Field(..., description="Result of integrity check: ok or error description")
    alembic_revision: Optional[str] = Field(None, description="Current Alembic migration revision head")
    database_size_bytes: int = Field(..., description="Database storage size on disk in bytes")
    database_size_mb: float = Field(..., description="Database storage size on disk in megabytes")
    table_counts: Dict[str, int] = Field(default_factory=dict, description="Row count per database table")
    wal_file_present: bool = Field(..., description="Whether Write-Ahead Log sidecar is present")
    last_backup: Optional[LastBackupDetail] = Field(None, description="Details of the latest verified backup snapshot")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC report timestamp")


class DatabaseBackupDetail(BaseModel):
    """Historical database backup record."""
    backup_id: str
    filename: str
    backup_path: str
    source_db: str
    created_at: str
    size_bytes: int
    size_mb: float
    sha256: str
    is_valid: bool
    integrity_status: str
    alembic_revision: Optional[str] = None
    tables_count: int = 0
    table_counts: Dict[str, int] = Field(default_factory=dict)


class DatabaseBackupListResponse(BaseModel):
    """List of available local verified backups."""
    backups: List[DatabaseBackupDetail]
    total: int


class DatabaseBackupCreateResponse(BaseModel):
    """Response returned upon successful manual database backup."""
    success: bool
    message: str
    backup: DatabaseBackupDetail

