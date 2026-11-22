"""
DateTime Tool for Universal Work Intelligence (Phase 05).
Provides current date/time, timezone adjustments, and duration computations.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

from backend.app.work.schemas import PermissionLevel, RiskLevel
from backend.app.work.tools.base import BaseTool


class DateTimeTool(BaseTool):
    """
    Safe and deterministic date/time utility.
    """

    @property
    def name(self) -> str:
        return "datetime_tool"

    @property
    def description(self) -> str:
        return (
            "Provides current date and time in ISO 8601 format, computes time differences, "
            "and performs date arithmetic (add/subtract offsets) with timezone awareness."
        )

    @property
    def category(self) -> str:
        return "datetime"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.AUTO_PERMIT

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["now", "diff", "add", "subtract"],
                    "description": "Operation to perform: 'now' (current timestamp), 'diff' (between date1 and date2), 'add' / 'subtract' (offset to date1)",
                    "default": "now"
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone name (e.g. 'UTC', 'America/New_York', 'Asia/Kolkata', 'local'). Defaults to local system timezone.",
                },
                "date1": {
                    "type": "string",
                    "description": "Primary ISO 8601 date/time string (e.g. '2026-11-19T18:00:00' or '2026-11-19'). Defaults to current time for add/subtract.",
                },
                "date2": {
                    "type": "string",
                    "description": "Secondary ISO 8601 date/time string for 'diff' action.",
                },
                "days": {"type": "integer", "description": "Days to add or subtract", "default": 0},
                "hours": {"type": "integer", "description": "Hours to add or subtract", "default": 0},
                "minutes": {"type": "integer", "description": "Minutes to add or subtract", "default": 0},
                "seconds": {"type": "integer", "description": "Seconds to add or subtract", "default": 0},
            },
            "required": []
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "timezone": {"type": "string"},
                "iso_timestamp": {"type": "string"},
                "formatted": {"type": "string"},
                "day_of_week": {"type": "string"},
                "epoch_timestamp": {"type": "number"},
                "diff_days": {"type": "number"},
                "diff_seconds": {"type": "number"},
                "result_timestamp": {"type": "string"}
            }
        }

    def _resolve_tz(self, tz_name: Optional[str]) -> timezone:
        if not tz_name or tz_name.lower() in ("local", "system"):
            return datetime.now().astimezone().tzinfo or timezone.utc
        try:
            return ZoneInfo(tz_name)
        except Exception:
            # Fallback for standard UTC/GMT or return local
            if tz_name.upper() in ("UTC", "GMT"):
                return timezone.utc
            return datetime.now().astimezone().tzinfo or timezone.utc

    def _parse_date(self, date_str: str, tz: timezone) -> datetime:
        # Try fromisoformat first
        try:
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            return dt
        except ValueError:
            pass

        # Try common formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz)
                return dt
            except ValueError:
                continue

        raise ValueError(f"Unable to parse date string: '{date_str}'. Expected ISO 8601 or YYYY-MM-DD.")

    async def run(self, **kwargs) -> Dict[str, Any]:
        action = kwargs.get("action", "now")
        tz_name = kwargs.get("timezone")
        tz = self._resolve_tz(tz_name)
        current_dt = datetime.now(tz)

        if action == "now":
            return {
                "action": "now",
                "timezone": str(tz),
                "iso_timestamp": current_dt.isoformat(),
                "formatted": current_dt.strftime("%A, %B %d, %Y %I:%M:%S %p %Z"),
                "date": current_dt.strftime("%Y-%m-%d"),
                "time": current_dt.strftime("%H:%M:%S"),
                "day_of_week": current_dt.strftime("%A"),
                "epoch_timestamp": current_dt.timestamp(),
            }

        elif action == "diff":
            d1_str = kwargs.get("date1")
            d2_str = kwargs.get("date2")
            if not d1_str or not d2_str:
                raise ValueError("Action 'diff' requires both 'date1' and 'date2' parameters.")
            d1 = self._parse_date(d1_str, tz)
            d2 = self._parse_date(d2_str, tz)
            delta = d2 - d1
            total_seconds = delta.total_seconds()
            return {
                "action": "diff",
                "date1": d1.isoformat(),
                "date2": d2.isoformat(),
                "diff_days": delta.days,
                "diff_total_seconds": total_seconds,
                "diff_hours": round(total_seconds / 3600.0, 2),
                "human_readable": f"{abs(delta.days)} days, {int((abs(total_seconds) % 86400) // 3600)} hours, {int((abs(total_seconds) % 3600) // 60)} minutes"
            }

        elif action in ("add", "subtract"):
            d1_str = kwargs.get("date1")
            base_dt = self._parse_date(d1_str, tz) if d1_str else current_dt
            offset = timedelta(
                days=int(kwargs.get("days", 0)),
                hours=int(kwargs.get("hours", 0)),
                minutes=int(kwargs.get("minutes", 0)),
                seconds=int(kwargs.get("seconds", 0)),
            )
            result_dt = base_dt + offset if action == "add" else base_dt - offset
            return {
                "action": action,
                "base_timestamp": base_dt.isoformat(),
                "result_timestamp": result_dt.isoformat(),
                "formatted": result_dt.strftime("%A, %B %d, %Y %I:%M:%S %p %Z"),
                "day_of_week": result_dt.strftime("%A"),
                "epoch_timestamp": result_dt.timestamp(),
            }

        else:
            raise ValueError(f"Unknown action '{action}'. Valid actions are 'now', 'diff', 'add', 'subtract'.")
