"""
Work Intelligence and Safe Tool Orchestration API Endpoints (Phase 05).
Provides authenticated endpoints for task lifecycle management, step execution,
tool discovery, and human-in-the-loop action approval.
"""

import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.authentication.dependencies import get_current_active_user
from backend.app.database.models.task import Task, TaskAction
from backend.app.database.models.user import User
from backend.app.database.session import get_db
from backend.app.work.exceptions import (
    ActionNotFoundError,
    TaskNotFoundError,
    ToolPermissionDeniedError,
)
from backend.app.work.schemas import (
    ActionApprovalRequest,
    ActionStatus,
    ApprovalState,
    PendingApprovalActionResponse,
    RiskLevel,
    TaskActionResponse,
    TaskCreateRequest,
    TaskResponse,
    TaskStatus,
    TaskStepPlan,
    ToolDefinition,
)
from backend.app.work.service import WorkService, get_work_service
from backend.app.work.tools.registry import ToolRegistry, get_tool_registry

router = APIRouter(prefix="/work", tags=["Work Intelligence & Safe Tools"])


def _serialize_action(action: TaskAction) -> TaskActionResponse:
    """Serializes a TaskAction ORM model to TaskActionResponse."""
    try:
        input_data = json.loads(action.input_json or "{}")
    except Exception:
        input_data = {}

    output_data = None
    if action.output_json:
        try:
            output_data = json.loads(action.output_json)
        except Exception:
            output_data = {"raw": action.output_json}

    return TaskActionResponse(
        id=action.id,
        task_id=action.task_id,
        step_index=action.step_index,
        title=action.title,
        tool_name=action.tool_name,
        risk_level=RiskLevel(action.risk_level),
        input=input_data,
        output=output_data,
        status=ActionStatus(action.status),
        approval_state=ApprovalState(action.approval_state),
        approved_by=action.approved_by,
        approved_at=action.approved_at,
        error_message=action.error_message,
        execution_time_ms=action.execution_time_ms,
        created_at=action.created_at,
        updated_at=action.updated_at,
    )


def _serialize_task(task: Task) -> TaskResponse:
    """Serializes a Task ORM model and nested actions to TaskResponse."""
    try:
        plan_raw = json.loads(task.plan_json or "[]")
        plan_steps = [TaskStepPlan(**p) if isinstance(p, dict) else p for p in plan_raw]
    except Exception:
        plan_steps = []

    action_responses = [
        _serialize_action(a)
        for a in sorted(task.actions, key=lambda x: x.step_index)
    ]

    return TaskResponse(
        id=task.id,
        user_id=task.user_id,
        conversation_id=task.conversation_id,
        title=task.title,
        description=task.description,
        status=TaskStatus(task.status),
        plan=plan_steps,
        actions=action_responses,
        result_summary=task.result_summary,
        error_message=task.error_message,
        total_steps=task.total_steps,
        completed_steps=task.completed_steps,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


# -----------------------------------------------------------------------------
# Tool Discovery Endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/tools",
    response_model=List[ToolDefinition],
    status_code=status.HTTP_200_OK,
    summary="List Registered Tools",
    description="Returns metadata catalog for all available tools with parameter schemas and risk tiers."
)
async def list_tools_endpoint(
    category: Optional[str] = Query(None, description="Filter tools by category"),
    max_risk: Optional[RiskLevel] = Query(None, description="Upper bound risk ceiling"),
    available_only: bool = Query(True, description="Exclude currently unavailable tools"),
    registry: ToolRegistry = Depends(get_tool_registry),
    current_user: User = Depends(get_current_active_user),
) -> List[ToolDefinition]:
    """Retrieve catalog of available safe tools."""
    return registry.list_tools(category=category, max_risk=max_risk, available_only=available_only)


# -----------------------------------------------------------------------------
# Task Lifecycle Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and Start Task",
    description="Deconstructs natural language goal into execution steps and initiates permitted actions."
)
async def create_task_endpoint(
    request: TaskCreateRequest,
    auto_execute: bool = Query(True, description="Immediately begin task execution"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: WorkService = Depends(get_work_service),
) -> TaskResponse:
    """Create and optionally start a new work intelligence task."""
    title = request.title or f"Task: {request.description[:60]}"
    task = await service.create_task(
        db=db,
        user_id=current_user.id,
        title=title,
        description=request.description,
        conversation_id=request.conversation_id,
    )

    if auto_execute:
        task = await service.execute_task(db=db, task_id=task.id, user_id=current_user.id)

    return _serialize_task(task)


@router.get(
    "/tasks",
    response_model=List[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List User Tasks",
    description="Lists all tasks created by the authenticated user with status filtering and pagination."
)
async def list_tasks_endpoint(
    status_filter: Optional[TaskStatus] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: WorkService = Depends(get_work_service),
) -> List[TaskResponse]:
    """List historical tasks with owner isolation."""
    status_val = status_filter.value if status_filter else None
    tasks = await service.list_tasks(
        db=db,
        user_id=current_user.id,
        status=status_val,
        limit=limit,
        offset=offset,
    )
    return [_serialize_task(t) for t in tasks]


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Task Details",
    description="Retrieves a specific task and its ordered actions. Strictly isolated to task owner."
)
async def get_task_endpoint(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: WorkService = Depends(get_work_service),
) -> TaskResponse:
    """Fetch complete task state and execution history."""
    try:
        task = await service.get_task(db=db, task_id=task_id, user_id=current_user.id)
        return _serialize_task(task)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/tasks/{task_id}/execute",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute or Resume Task",
    description="Executes remaining permitted actions in a pending or paused task."
)
async def execute_task_endpoint(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: WorkService = Depends(get_work_service),
) -> TaskResponse:
    """Execute or resume an existing task."""
    try:
        task = await service.execute_task(db=db, task_id=task_id, user_id=current_user.id)
        return _serialize_task(task)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Task",
    description="Cancels an in-progress or waiting task and aborts pending actions."
)
async def cancel_task_endpoint(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: WorkService = Depends(get_work_service),
) -> TaskResponse:
    """Cancel an active task."""
    try:
        task = await service.cancel_task(db=db, task_id=task_id, user_id=current_user.id)
        return _serialize_task(task)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# -----------------------------------------------------------------------------
# Approval & Confirmation Endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/approvals",
    response_model=List[PendingApprovalActionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Pending Approvals",
    description="Retrieves all actions awaiting explicit user authorization."
)
async def list_pending_approvals_endpoint(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: WorkService = Depends(get_work_service),
) -> List[PendingApprovalActionResponse]:
    """Retrieve all pending approval requests for current user."""
    actions = await service.list_pending_approvals(db=db, user_id=current_user.id)
    results: List[PendingApprovalActionResponse] = []
    for action in actions:
        results.append(
            PendingApprovalActionResponse(
                task_id=action.task_id,
                task_title=action.task.title if action.task else f"Task {action.task_id}",
                action=_serialize_action(action),
            )
        )
    return results


@router.post(
    "/approvals/{action_id}",
    response_model=TaskActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Respond to Action Approval",
    description="Authorizes or rejects a pending tool action, automatically resuming execution on approval."
)
async def respond_to_approval_endpoint(
    action_id: str,
    request: ActionApprovalRequest,
    auto_resume: bool = Query(True, description="Automatically resume parent task upon approval"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: WorkService = Depends(get_work_service),
) -> TaskActionResponse:
    """Explicitly approve or reject a pending tool execution."""
    try:
        action = await service.respond_to_approval(
            db=db,
            action_id=action_id,
            user_id=current_user.id,
            approved=request.approved,
            auto_resume=auto_resume,
        )
        return _serialize_action(action)
    except ActionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ToolPermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
