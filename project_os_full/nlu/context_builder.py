from __future__ import annotations

from typing import Any

from .context_manager import ContextManager


class ContextBuilder:
    """Build the provider payload without exposing mutable context state."""

    def __init__(self, context_manager: ContextManager) -> None:
        self.context_manager = context_manager

    def build(
        self,
        current_text: str,
        candidate: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = (
            self.context_manager.get_context()
            if self.context_manager.has_pending()
            else None
        )
        return {
            "current_text": current_text,
            "candidate": candidate,
            "context": context,
        }

