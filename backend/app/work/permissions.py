"""
Permission and Security Engine for Universal Work Intelligence (Phase 05).
Evaluates operational risk tiers, enforces human-in-the-loop consent policies,
and guards against unauthorized tool actions.
"""

from typing import Optional, Tuple
from backend.app.config.settings import get_settings
from backend.app.work.exceptions import ToolPermissionDeniedError
from backend.app.work.schemas import ApprovalState, PermissionLevel, RiskLevel
from backend.app.work.tools.base import BaseTool


class PermissionManager:
    """
    Evaluates and enforces execution authorization based on tool risk profiles
    and human-in-the-loop approval state.
    """

    def __init__(self, require_medium_confirmation: Optional[bool] = None):
        settings = get_settings()
        self._require_medium_confirmation = (
            require_medium_confirmation
            if require_medium_confirmation is not None
            else settings.TOOL_REQUIRE_CONFIRMATION_FOR_MEDIUM_RISK
        )

    def requires_approval(self, tool: BaseTool) -> bool:
        """
        Determines whether executing the tool requires explicit human approval
        prior to runtime invocation.
        """
        if tool.risk_level == RiskLevel.HIGH:
            return True
        if tool.risk_level == RiskLevel.MEDIUM and self._require_medium_confirmation:
            return True
        return False

    def get_initial_approval_state(self, tool: BaseTool) -> ApprovalState:
        """
        Returns the initial ApprovalState for a new action.
        """
        if self.requires_approval(tool):
            return ApprovalState.PENDING_APPROVAL
        return ApprovalState.APPROVED

    def evaluate_permission(
        self,
        tool: BaseTool,
        approval_state: ApprovalState = ApprovalState.NOT_REQUIRED,
    ) -> Tuple[bool, str]:
        """
        Evaluates whether an action is currently permitted to execute.
        Returns (is_permitted, reason_message).
        """
        # Low risk actions are auto-permitted
        if tool.risk_level == RiskLevel.LOW:
            return True, "Low risk operation auto-permitted."

        # High risk operations strictly require explicit approval
        if tool.risk_level == RiskLevel.HIGH:
            if approval_state == ApprovalState.APPROVED:
                return True, "High risk operation explicitly approved by user."
            return False, f"High risk tool '{tool.name}' requires explicit user approval before execution."

        # Medium risk operations
        if tool.risk_level == RiskLevel.MEDIUM:
            if not self._require_medium_confirmation or approval_state == ApprovalState.APPROVED:
                return True, "Medium risk operation permitted."
            return False, f"Tool '{tool.name}' modifies workspace and requires user confirmation."

        return False, "Unknown permission policy."

    def validate_execution_guard(
        self,
        tool: BaseTool,
        approval_state: ApprovalState = ApprovalState.NOT_REQUIRED,
    ) -> None:
        """
        Validates permission immediately prior to execution, raising
        ToolPermissionDeniedError if authorization criteria are not met.
        """
        permitted, reason = self.evaluate_permission(tool, approval_state)
        if not permitted:
            raise ToolPermissionDeniedError(tool.name, reason)


_default_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Returns singleton PermissionManager instance."""
    global _default_permission_manager
    if _default_permission_manager is None:
        _default_permission_manager = PermissionManager()
    return _default_permission_manager
