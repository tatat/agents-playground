"""Logging middleware for token usage tracking."""

from typing import Any

import rich
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
)


class TokenUsageLoggingMiddleware(AgentMiddleware[AgentState[Any], Any]):
    """Middleware that logs token usage for each model call."""

    def after_model(self, state: AgentState[Any], runtime: Any) -> dict[str, Any] | None:  # noqa: ARG002
        """Log token usage after model call."""
        # Get the last message from state which contains usage metadata
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            usage = getattr(last_msg, "usage_metadata", None)
            if usage is not None:
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)

                # Check for cache usage
                input_details = usage.get("input_token_details", {})
                cache_read = input_details.get("cache_read", 0)

                if cache_read:
                    rich.print(f"\n[dim]Tokens: {input_tokens} in (cache: {cache_read}) / {output_tokens} out[/dim]")
                else:
                    rich.print(f"\n[dim]Tokens: {input_tokens} in / {output_tokens} out[/dim]")

        return None
