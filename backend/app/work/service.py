"""
Work Service for Universal Work Intelligence (Phase 05).
Coordinates task lifecycle, step planning, execution tracking, approval states,
and historical persistence with strict owner-level isolation.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.database.models.task import Task, TaskAction
from backend.app.work.exceptions import (
    ActionNotFoundError,
    TaskNotFoundError,
    ToolPermissionDeniedError,
)
from backend.app.work.executor import TaskExecutor, get_task_executor
from backend.app.work.permissions import PermissionManager, get_permission_manager
from backend.app.work.planner import TaskPlanner
from backend.app.work.schemas import (
    ActionStatus,
    ApprovalState,
    RiskLevel,
    TaskStatus,
    TaskStepPlan,
)
from backend.app.work.tools.registry import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)


class WorkService:
    """
    Central service orchestrating work intelligence, task plans, tool executions,
    and user approval workflows.
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        permission_manager: Optional[PermissionManager] = None,
        executor: Optional[TaskExecutor] = None,
        planner: Optional[TaskPlanner] = None,
    ):
        self._registry = registry or get_tool_registry()
        self._permission_manager = permission_manager or get_permission_manager()
        self._executor = executor or get_task_executor()
        self._planner = planner or TaskPlanner(self._registry)

    async def create_task(
        self,
        db: AsyncSession,
        user_id: str,
        title: str,
        description: str,
        conversation_id: Optional[str] = None,
        plan_steps: Optional[List[TaskStepPlan]] = None,
    ) -> Task:
        """
        Plans and persists a new multi-step task for the user.
        """
        # 1. Plan steps if not pre-provided
        if plan_steps is None:
            plan_steps = self._planner.plan_task(goal=description)

        plan_dicts = [step.model_dump() for step in plan_steps]

        # 2. Instantiate Task entity
        task = Task(
            user_id=user_id,
            conversation_id=conversation_id,
            title=title,
            description=description,
            status=TaskStatus.PENDING.value,
            plan_json=json.dumps(plan_dicts),
            total_steps=len(plan_steps),
            completed_steps=0,
        )
        db.add(task)
        await db.flush()  # Generate task.id

        # 3. Create TaskAction entities for each step
        for step in plan_steps:
            # Check if tool requires approval
            needs_approval = False
            if self._registry.has(step.tool_name):
                tool = self._registry.get(step.tool_name)
                needs_approval = self._permission_manager.requires_approval(tool)

            init_approval = ApprovalState.PENDING.value if needs_approval else ApprovalState.NOT_REQUIRED.value
            init_status = ActionStatus.AWAITING_APPROVAL.value if needs_approval else ActionStatus.PENDING.value

            # Idempotency hash based on task_id, step, and arguments
            raw_key = f"{task.id}:{step.step_number}:{step.tool_name}:{json.dumps(step.arguments, sort_keys=True)}"
            idempotency_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

            action = TaskAction(
                task_id=task.id,
                step_index=step.step_number,
                title=step.description,
                tool_name=step.tool_name,
                risk_level=step.risk_level.value,
                input_json=json.dumps(step.arguments),
                status=init_status,
                approval_state=init_approval,
                idempotency_key=idempotency_key,
            )
            db.add(action)

        await db.commit()
        await db.refresh(task)

        # Record synchronization event
        try:
            from backend.app.sync.service import get_sync_service
            await get_sync_service().record_event(
                db=db,
                user_id=user_id,
                entity_type="task",
                entity_id=task.id,
                action="created",
                payload={
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "total_steps": task.total_steps,
                    "completed_steps": task.completed_steps,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                }
            )
            await db.commit()
        except Exception as exc:
            logger.debug(f"Sync event recording skipped for task creation: {exc}")

        return await self.get_task(db=db, task_id=task.id, user_id=user_id)

    async def get_task(self, db: AsyncSession, task_id: str, user_id: str) -> Task:
        """
        Retrieves a task with its ordered actions, enforcing owner isolation.
        """
        stmt = (
            select(Task)
            .options(selectinload(Task.actions))
            .where(Task.id == task_id, Task.user_id == user_id)
        )
        result = await db.execute(stmt)
        task = result.scalars().first()
        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found or access denied.")
        return task

    async def list_tasks(
        self,
        db: AsyncSession,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Task]:
        """
        Lists tasks owned by user with pagination and optional status filter.
        """
        stmt = (
            select(Task)
            .options(selectinload(Task.actions))
            .where(Task.user_id == user_id)
            .order_by(desc(Task.created_at))
            .offset(offset)
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Task.status == status)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def execute_task(self, db: AsyncSession, task_id: str, user_id: str) -> Task:
        """
        Executes pending steps of a task, pausing when approvals are required
        and synthesizing the final result upon completion.
        """
        task = await self.get_task(db=db, task_id=task_id, user_id=user_id)

        if task.status in (TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value):
            return task

        task.status = TaskStatus.IN_PROGRESS.value
        await db.commit()

        # Execute actions in step order
        completed_count = 0
        step_summaries: List[str] = []

        for action in sorted(task.actions, key=lambda a: a.step_index):
            if action.status == ActionStatus.COMPLETED.value:
                completed_count += 1
                step_summaries.append(f"Step {action.step_index} ({action.title}): Completed")
                continue

            # Check if action requires user approval
            if action.approval_state == ApprovalState.PENDING.value:
                action.status = ActionStatus.AWAITING_APPROVAL.value
                task.status = TaskStatus.AWAITING_APPROVAL.value
                await db.commit()
                logger.info(f"Task '{task.id}' waiting for approval on step {action.step_index} ('{action.title}')")
                return await self.get_task(db=db, task_id=task.id, user_id=user_id)

            if action.approval_state == ApprovalState.REJECTED.value:
                action.status = ActionStatus.REJECTED.value
                task.status = TaskStatus.FAILED.value
                task.error_message = f"Step {action.step_index} ('{action.title}') was rejected by user."
                task.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return await self.get_task(db=db, task_id=task.id, user_id=user_id)

            # Verify action integrity against planning idempotency hash
            args = json.loads(action.input_json or "{}")
            raw_key = f"{task.id}:{action.step_index}:{action.tool_name}:{json.dumps(args, sort_keys=True)}"
            expected_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
            if action.idempotency_key and action.idempotency_key != expected_key:
                action.status = ActionStatus.FAILED.value
                action.error_message = "Integrity check failed: action parameters do not match planning idempotency key."
                task.status = TaskStatus.FAILED.value
                task.error_message = action.error_message
                task.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return await self.get_task(db=db, task_id=task.id, user_id=user_id)

            # Execute action
            action.status = ActionStatus.RUNNING.value
            await db.commit()

            approval_enum = ApprovalState(action.approval_state)

            result = await self._executor.execute_tool(
                tool_name=action.tool_name,
                arguments=args,
                approval_state=approval_enum,
            )

            action.execution_time_ms = result.execution_time_ms
            if result.is_success:
                action.status = ActionStatus.COMPLETED.value
                action.output_json = json.dumps(result.output)
                completed_count += 1
                task.completed_steps = completed_count
                await db.commit()

                # Add to summary
                out_snippet = ""
                if isinstance(result.output, dict):
                    if "formatted" in result.output:
                        out_snippet = result.output["formatted"]
                    elif "result" in result.output:
                        out_snippet = f"= {result.output['result']}"
                    elif "message" in result.output:
                        out_snippet = result.output["message"]
                    elif "total_items" in result.output:
                        out_snippet = f"Found {result.output['total_items']} items"
                    elif "total_matches" in result.output:
                        out_snippet = f"Found {result.output['total_matches']} matches"
                    elif "total_findings" in result.output:
                        out_snippet = f"Found {result.output['total_findings']} citations"
                    else:
                        out_snippet = "Success"
                step_summaries.append(f"Step {action.step_index} ({action.title}): {out_snippet}")
            else:
                action.status = ActionStatus.FAILED.value
                action.error_message = result.error
                task.status = TaskStatus.FAILED.value
                task.error_message = f"Step {action.step_index} ('{action.title}') failed: {result.error}"
                task.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return await self.get_task(db=db, task_id=task.id, user_id=user_id)

        # All steps successfully completed
        task.status = TaskStatus.COMPLETED.value
        task.completed_steps = completed_count
        task.completed_at = datetime.now(timezone.utc)
        task.result_summary = "\n".join(step_summaries) if step_summaries else "Task successfully completed all operations."
        await db.commit()

        # Record synchronization event
        try:
            from backend.app.sync.service import get_sync_service
            await get_sync_service().record_event(
                db=db,
                user_id=user_id,
                entity_type="task",
                entity_id=task.id,
                action="updated",
                payload={
                    "id": task.id,
                    "status": task.status,
                    "completed_steps": task.completed_steps,
                    "total_steps": task.total_steps,
                    "result_summary": task.result_summary,
                }
            )
            await db.commit()
        except Exception as exc:
            logger.debug(f"Sync event recording skipped for task completion: {exc}")

        return await self.get_task(db=db, task_id=task.id, user_id=user_id)

    async def cancel_task(self, db: AsyncSession, task_id: str, user_id: str) -> Task:
        """
        Cancels an in-progress or awaiting-approval task.
        """
        task = await self.get_task(db=db, task_id=task_id, user_id=user_id)
        if task.status in (TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value):
            return task

        task.status = TaskStatus.CANCELLED.value
        task.completed_at = datetime.now(timezone.utc)
        task.error_message = "Task cancelled by user."

        for action in task.actions:
            if action.status in (ActionStatus.PENDING.value, ActionStatus.AWAITING_APPROVAL.value):
                action.status = ActionStatus.CANCELLED.value

        await db.commit()
        return await self.get_task(db=db, task_id=task.id, user_id=user_id)

    async def resume_task(self, db: AsyncSession, task_id: str, user_id: str) -> Task:
        """
        Resumes execution of a paused or awaiting-approval task.
        """
        return await self.execute_task(db=db, task_id=task_id, user_id=user_id)

    async def list_pending_approvals(self, db: AsyncSession, user_id: str) -> List[TaskAction]:
        """
        Lists all task actions pending user approval for the given user.
        """
        stmt = (
            select(TaskAction)
            .options(selectinload(TaskAction.task))
            .join(Task, TaskAction.task_id == Task.id)
            .where(
                Task.user_id == user_id,
                TaskAction.approval_state == ApprovalState.PENDING.value,
            )
            .order_by(TaskAction.created_at)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def respond_to_approval(
        self,
        db: AsyncSession,
        action_id: str,
        user_id: str,
        approved: bool,
        auto_resume: bool = True,
    ) -> TaskAction:
        """
        Records human approval or rejection of an action and optionally resumes task execution.
        """
        stmt = (
            select(TaskAction)
            .join(Task, TaskAction.task_id == Task.id)
            .where(TaskAction.id == action_id, Task.user_id == user_id)
        )
        result = await db.execute(stmt)
        action = result.scalars().first()
        if not action:
            raise ActionNotFoundError(f"Action '{action_id}' not found or access denied.")

        # Replay protection: only pending actions can be approved/rejected
        if action.approval_state != ApprovalState.PENDING.value:
            raise ToolPermissionDeniedError(
                action.tool_name,
                f"Approval cannot be replayed: action is already '{action.approval_state}'"
            )

        # Expiration check (24 hour approval window)
        created_dt = action.created_at
        if created_dt:
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - created_dt).total_seconds()
            if age_seconds > 86400:  # 24 hours
                action.approval_state = ApprovalState.REJECTED.value
                action.status = ActionStatus.REJECTED.value
                action.error_message = "Approval request has expired (window: 24h)."
                await db.commit()
                raise ToolPermissionDeniedError(
                    action.tool_name,
                    "Approval request has expired."
                )

        action.approved_by = user_id
        action.approved_at = datetime.now(timezone.utc)

        if approved:
            action.approval_state = ApprovalState.APPROVED.value
            action.status = ActionStatus.APPROVED.value
        else:
            action.approval_state = ApprovalState.REJECTED.value
            action.status = ActionStatus.REJECTED.value

        await db.commit()
        await db.refresh(action)

        # Record synchronization event for action approval
        try:
            from backend.app.sync.service import get_sync_service
            await get_sync_service().record_event(
                db=db,
                user_id=user_id,
                entity_type="action_approval",
                entity_id=action.id,
                action="updated",
                payload={
                    "id": action.id,
                    "task_id": action.task_id,
                    "step_index": action.step_index,
                    "tool_name": action.tool_name,
                    "approval_state": action.approval_state,
                    "status": action.status,
                    "approved_by": action.approved_by,
                    "approved_at": action.approved_at.isoformat() if action.approved_at else None,
                }
            )
            await db.commit()
        except Exception as exc:
            logger.debug(f"Sync event recording skipped for action approval: {exc}")

        if auto_resume:
            # Resume parent task execution
            await self.execute_task(db=db, task_id=action.task_id, user_id=user_id)

        return action


_default_work_service: Optional[WorkService] = None


def get_work_service() -> WorkService:
    """Returns singleton WorkService instance."""
    global _default_work_service
    if _default_work_service is None:
        _default_work_service = WorkService()
    return _default_work_service
