"""
System Observability and Hardware Metrics API Endpoints (Phase 08).
Provides live, authoritative system resource telemetry and a unified activity timeline.
"""

import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import psutil
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.endpoints.health import _START_TIME
from backend.app.authentication.dependencies import get_current_active_user
from backend.app.config.settings import get_settings
from backend.app.database.models.conversation import Conversation
from backend.app.database.models.device import Device
from backend.app.database.models.memory import Memory
from backend.app.database.models.task import Task, TaskAction
from backend.app.database.models.user import User
from backend.app.database.session import get_database_diagnostics, get_db
from backend.app.database.backup import create_database_backup, list_database_backups
from backend.app.schemas.system import (
    DatabaseBackupCreateResponse,
    DatabaseBackupDetail,
    DatabaseBackupListResponse,
    DatabaseHealthResponse,
    GpuMetrics,
    LocalModelStatus,
    RamMetrics,
    SystemActivityItem,
    SystemActivityResponse,
    SystemMetricsResponse,
)

router = APIRouter(prefix="/system", tags=["System Observability"])
settings = get_settings()


def _ensure_utc(dt: Optional[datetime]) -> datetime:
    """Normalize naive or aware datetime to UTC."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get(
    "/metrics",
    response_model=SystemMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Live Hardware Resource Metrics",
    description="Returns authoritative real-time CPU, RAM, GPU, and VRAM measurements. Never returns simulated values."
)
async def get_system_metrics_endpoint(
    current_user: User = Depends(get_current_active_user),
) -> SystemMetricsResponse:
    """Collects authoritative, un-simulated hardware telemetry."""
    # 1. CPU
    cpu_percent = psutil.cpu_percent(interval=None)

    # 2. RAM
    vmem = psutil.virtual_memory()
    ram_metrics = RamMetrics(
        used_gb=round(vmem.used / (1024**3), 2),
        total_gb=round(vmem.total / (1024**3), 2),
        percent=vmem.percent,
    )

    # 3. GPU & VRAM
    gpu_metrics = GpuMetrics(
        available=False,
        name="Unavailable",
        vram_used_gb=None,
        vram_total_gb=None,
        vram_percent=None,
        utilization_percent=None,
    )

    try:
        import torch
        if torch.cuda.is_available():
            gpu_metrics.available = True
            gpu_metrics.name = torch.cuda.get_device_name(0)
            try:
                free, total = torch.cuda.mem_get_info(0)
                used = total - free
                gpu_metrics.vram_used_gb = round(used / (1024**3), 2)
                gpu_metrics.vram_total_gb = round(total / (1024**3), 2)
                gpu_metrics.vram_percent = round((used / total) * 100, 1)
            except Exception:
                pass
    except ImportError:
        pass

    # Real GPU utilization from nvidia-smi if available
    try:
        smi_res = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=0.6,
        )
        if smi_res.returncode == 0 and smi_res.stdout.strip():
            first_line = smi_res.stdout.strip().split("\n")[0]
            gpu_metrics.utilization_percent = float(first_line)
    except Exception:
        pass

    # 4. Local Model Service (Ollama ping)
    local_status = LocalModelStatus(
        is_running=False,
        service_name="ollama",
        latency_ms=None,
        error=None,
    )

    try:
        ollama_url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/version"
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=0.8) as client:
            resp = await client.get(ollama_url)
            if resp.status_code == 200:
                local_status.is_running = True
                local_status.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            else:
                local_status.error = f"HTTP {resp.status_code}"
    except Exception as exc:
        local_status.error = str(exc)

    uptime = round(time.perf_counter() - _START_TIME, 2)

    return SystemMetricsResponse(
        cpu_percent=cpu_percent,
        ram=ram_metrics,
        gpu=gpu_metrics,
        local_model=local_status,
        uptime_seconds=uptime,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/activity",
    response_model=SystemActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Unified Activity Timeline",
    description="Returns genuine chronological timeline of system events across conversations, tasks, memory, and devices."
)
async def get_system_activity_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SystemActivityResponse:
    """Builds unified activity timeline from real database records."""
    activity_items: List[SystemActivityItem] = []

    # 1. Conversations
    try:
        conv_stmt = (
            select(Conversation)
            .where(Conversation.user_id == current_user.id)
            .order_by(Conversation.created_at.desc())
            .limit(15)
        )
        convs = (await db.execute(conv_stmt)).scalars().all()
        for c in convs:
            activity_items.append(
                SystemActivityItem(
                    id=f"conv-{c.id}",
                    event_type="conversation_created",
                    title=f"Started: {c.title}",
                    description=None,
                    category="intelligence",
                    timestamp=_ensure_utc(c.created_at),
                    metadata={"conversation_id": c.id},
                )
            )
    except Exception:
        pass

    # 2. Tasks & Action Approvals
    try:
        task_stmt = (
            select(Task)
            .where(Task.user_id == current_user.id)
            .order_by(Task.created_at.desc())
            .limit(15)
        )
        tasks = (await db.execute(task_stmt)).scalars().all()
        for t in tasks:
            # Created
            activity_items.append(
                SystemActivityItem(
                    id=f"task-create-{t.id}",
                    event_type="task_created",
                    title=f"Task Created: {t.title}",
                    description=t.description[:90] if t.description else None,
                    category="work",
                    timestamp=_ensure_utc(t.created_at),
                    metadata={"task_id": t.id, "status": t.status},
                )
            )
            # Completed or Failed
            if t.status == "completed" and t.completed_at:
                activity_items.append(
                    SystemActivityItem(
                        id=f"task-done-{t.id}",
                        event_type="task_completed",
                        title=f"Task Completed: {t.title}",
                        description=t.result_summary[:90] if t.result_summary else None,
                        category="work",
                        timestamp=_ensure_utc(t.completed_at),
                        metadata={"task_id": t.id, "steps": t.completed_steps},
                    )
                )
            elif t.status == "failed" and t.updated_at:
                activity_items.append(
                    SystemActivityItem(
                        id=f"task-fail-{t.id}",
                        event_type="task_failed",
                        title=f"Task Failed: {t.title}",
                        description=t.error_message[:90] if t.error_message else None,
                        category="work",
                        timestamp=_ensure_utc(t.updated_at),
                        metadata={"task_id": t.id},
                    )
                )

        # Task Actions (Approvals)
        action_stmt = (
            select(TaskAction)
            .join(Task, TaskAction.task_id == Task.id)
            .where(Task.user_id == current_user.id)
            .order_by(TaskAction.created_at.desc())
            .limit(15)
        )
        actions = (await db.execute(action_stmt)).scalars().all()
        for a in actions:
            if a.approval_state == "pending":
                activity_items.append(
                    SystemActivityItem(
                        id=f"action-pend-{a.id}",
                        event_type="action_awaiting_approval",
                        title=f"Approval Pending: {a.title}",
                        description=f"Tool: {a.tool_name} (Risk: {a.risk_level})",
                        category="work",
                        timestamp=_ensure_utc(a.created_at),
                        metadata={"action_id": a.id, "task_id": a.task_id},
                    )
                )
            elif a.approval_state == "approved" and a.approved_at:
                activity_items.append(
                    SystemActivityItem(
                        id=f"action-appr-{a.id}",
                        event_type="action_approved",
                        title=f"Action Authorized: {a.title}",
                        description=f"Tool: {a.tool_name} authorized by {a.approved_by or 'User'}",
                        category="work",
                        timestamp=_ensure_utc(a.approved_at),
                        metadata={"action_id": a.id, "task_id": a.task_id},
                    )
                )
            elif a.approval_state == "rejected":
                activity_items.append(
                    SystemActivityItem(
                        id=f"action-rej-{a.id}",
                        event_type="action_rejected",
                        title=f"Action Rejected: {a.title}",
                        description=f"Tool: {a.tool_name} execution denied",
                        category="work",
                        timestamp=_ensure_utc(a.updated_at),
                        metadata={"action_id": a.id, "task_id": a.task_id},
                    )
                )
    except Exception:
        pass

    # 3. Memories
    try:
        mem_stmt = (
            select(Memory)
            .where(Memory.user_id == current_user.id)
            .order_by(Memory.created_at.desc())
            .limit(15)
        )
        mems = (await db.execute(mem_stmt)).scalars().all()
        for m in mems:
            activity_items.append(
                SystemActivityItem(
                    id=f"mem-{m.id}",
                    event_type="memory_saved",
                    title=f"Memory Saved ({m.category.capitalize()})",
                    description=m.content[:80] + ("..." if len(m.content) > 80 else ""),
                    category="memory",
                    timestamp=_ensure_utc(m.created_at),
                    metadata={"memory_id": m.id, "category": m.category},
                )
            )
    except Exception:
        pass

    # 4. Devices
    try:
        dev_stmt = (
            select(Device)
            .where(Device.user_id == current_user.id)
            .order_by(Device.created_at.desc())
            .limit(10)
        )
        devs = (await db.execute(dev_stmt)).scalars().all()
        for d in devs:
            activity_items.append(
                SystemActivityItem(
                    id=f"dev-{d.id}",
                    event_type="device_registered",
                    title=f"Device: {d.device_name}",
                    description=f"{d.device_type.capitalize()} • Client v{d.client_version or '1.0'}",
                    category="security",
                    timestamp=_ensure_utc(d.created_at),
                    metadata={"device_id": d.id, "is_trusted": d.is_trusted},
                )
            )
    except Exception:
        pass

    # Sort all events chronologically (newest first)
    activity_items.sort(key=lambda x: x.timestamp, reverse=True)

    # Slice to requested limit
    paged_items = activity_items[:limit]

    return SystemActivityResponse(
        items=paged_items,
        total=len(paged_items),
    )


@router.get(
    "/database",
    response_model=DatabaseHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Database Architecture & Health Diagnostics",
    description="Returns authenticated real-time database engine status, latency, WAL mode, integrity check, migration revision, file size, table counts, and latest backup info. Never exposes credentials."
)
async def get_database_health_endpoint(
    current_user: User = Depends(get_current_active_user),
) -> DatabaseHealthResponse:
    """Returns database operational health and diagnostics."""
    diagnostics = await get_database_diagnostics()
    return DatabaseHealthResponse(**diagnostics)


@router.post(
    "/database/backup",
    response_model=DatabaseBackupCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Atomic Database Backup",
    description="Triggers an atomic, WAL-safe SQLite backup with post-backup integrity validation and SHA-256 metadata generation."
)
async def create_database_backup_endpoint(
    current_user: User = Depends(get_current_active_user),
) -> DatabaseBackupCreateResponse:
    """Creates a verified database backup snapshot."""
    metadata = create_database_backup()
    return DatabaseBackupCreateResponse(
        success=True,
        message="Database backup created and verified successfully",
        backup=DatabaseBackupDetail(**metadata),
    )


@router.get(
    "/database/backups",
    response_model=DatabaseBackupListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Historical Database Backups",
    description="Returns chronological inventory of available verified database backups."
)
async def list_database_backups_endpoint(
    current_user: User = Depends(get_current_active_user),
) -> DatabaseBackupListResponse:
    """Lists available database backups."""
    backups = list_database_backups()
    backup_details = [DatabaseBackupDetail(**b) for b in backups]
    return DatabaseBackupListResponse(
        backups=backup_details,
        total=len(backup_details),
    )

