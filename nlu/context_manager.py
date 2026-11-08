from __future__ import annotations

from typing import Any


class ContextManager:
    """Store only the short-lived state needed for a follow-up turn."""

    def __init__(self):
        self.pending_action = None
        self.pending_target = None
        self.last_command = None

        self.pending_params = {}
        self.pending_kind = None
        self.pending_score = 0.0

    def set_pending(
        self,
        action: str | None,
        target: str | None = None,
        command: str | None = None,
        params: dict[str, Any] | None = None,
        kind: str | None = "clarification",
        score: float = 0.0,
    ) -> None:
        self.pending_action = action
        self.pending_target = target
        self.last_command = command

        self.pending_params = (
            dict(params)
            if isinstance(params, dict)
            else {}
        )

        self.pending_kind = kind
        self.pending_score = score

    def get_context(self) -> dict[str, Any]:
        return {
            "pending_action": self.pending_action,
            "pending_target": self.pending_target,
            "last_command": self.last_command,
            "pending_params": dict(self.pending_params),
            "pending_kind": self.pending_kind,
            "pending_score": self.pending_score,
        }


    def get_pending_state(self) -> dict[str, Any]:
        return {
            "pending_action": self.pending_action,
            "pending_target": self.pending_target,
            "last_command": self.last_command,
            "pending_params": dict(self.pending_params),
            "pending_kind": self.pending_kind,
            "pending_score": self.pending_score,
        }

    def has_pending(self) -> bool:
        return (
            self.pending_kind is not None
            or self.pending_action is not None
        )

    def clear(self) -> None:
        self.pending_action = None
        self.pending_target = None
        self.last_command = None

        self.pending_params = {}
        self.pending_kind = None
        self.pending_score = 0.0
