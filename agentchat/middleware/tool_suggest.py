"""Tool suggestion middleware for automatic tool recommendations."""

from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import rich
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import HumanMessage, SystemMessage

from ..tools.embeddings import encode_query
from ..tools.registry import TOOL_REGISTRY
from ..tools.tool_search import get_tool_index


class ToolSuggestMiddleware(AgentMiddleware[AgentState[Any], Any]):
    """Middleware that suggests relevant tools based on user message.

    Searches for tools matching the latest user message and injects
    suggestions into the system prompt before model call.
    """

    SUGGEST_START = "[TOOL_SUGGESTIONS]"
    SUGGEST_END = "[/TOOL_SUGGESTIONS]"

    def __init__(self, top_k: int = 3):
        """Initialize middleware.

        Args:
            top_k: Number of tools to suggest.
        """
        self.top_k = top_k
        self._index_available: bool | None = None  # None = not checked yet
        self._last_user_message: str | None = None  # Skip search if same message

    def _get_latest_user_message(self, messages: Sequence[Any]) -> str | None:
        """Extract the latest user message content."""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                content = msg.content
                if isinstance(content, str):
                    return content
                # Handle list content (multimodal)
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text = item.get("text")
                            if isinstance(text, str):
                                return text
        return None

    def _search_tools(self, query: str) -> list[dict[str, Any]]:
        """Search for relevant tools. Returns empty list on failure."""
        # Skip if we know index is unavailable
        if self._index_available is False:
            return []

        try:
            index = get_tool_index()

            # Build index if not yet built
            if index.table is None:
                index.build_index(TOOL_REGISTRY)

            self._index_available = True

            # Use shared embeddings with cache to avoid duplicate encoding
            vector = encode_query(query)
            return index.search_with_vector(vector, query, self.top_k)
        except Exception as e:  # noqa: BLE001
            # Log once and disable future attempts
            if self._index_available is None:
                rich.print(f"[dim]Tool search unavailable: {e}[/dim]")
            self._index_available = False
            return []

    def _build_suggestion_text(self, tools: list[dict[str, Any]]) -> str:
        """Build suggestion text to inject into prompt, wrapped with markers."""
        if not tools:
            return ""

        lines = [self.SUGGEST_START]
        lines.append("Suggested tools based on user's request:")
        for t in tools:
            name = t.get("name", "?")
            desc = t.get("description", "")
            lines.append(f"- {name}: {desc}")
        lines.append("Use tool_search_regex('^name$') to enable these tools.")
        lines.append(self.SUGGEST_END)

        return "\n".join(lines)

    def _remove_old_suggestion(self, content: str) -> str:
        """Remove existing suggestion block from content."""
        start_idx = content.find(self.SUGGEST_START)
        if start_idx == -1:
            return content

        end_idx = content.find(self.SUGGEST_END)
        if end_idx == -1:
            return content

        # Remove the suggestion block including markers
        end_idx += len(self.SUGGEST_END)
        # Also remove surrounding whitespace
        before = content[:start_idx].rstrip()
        after = content[end_idx:].lstrip()

        if before and after:
            return f"{before}\n\n{after}"
        return before or after

    def _update_system_message(
        self, system_message: SystemMessage | None, suggestion: str | None
    ) -> SystemMessage | None:
        """Update system message with suggestion, replacing old one if present.

        If suggestion is None or empty, removes old suggestions from the message.
        Preserves original message metadata (additional_kwargs, response_metadata, id).
        """
        if system_message is None:
            if suggestion:
                return SystemMessage(content=suggestion)
            return None

        content = system_message.content if isinstance(system_message.content, str) else str(system_message.content)
        clean_content = self._remove_old_suggestion(content)

        # Build new content: clean content + suggestion (if any)
        if suggestion:
            new_content = f"{clean_content}\n\n{suggestion}"
        else:
            new_content = clean_content

        # Preserve original message fields
        return SystemMessage(
            content=new_content,
            additional_kwargs=system_message.additional_kwargs,
            response_metadata=system_message.response_metadata,
            id=system_message.id,
        )

    def _process_request(self, request: ModelRequest) -> ModelRequest:
        """Process request: search tools and update system message."""
        user_msg = self._get_latest_user_message(request.messages)
        if not user_msg:
            return request

        # Skip search if same user message (e.g., tool call loop)
        if user_msg == self._last_user_message:
            return request

        self._last_user_message = user_msg
        tools = self._search_tools(user_msg)
        suggestion = self._build_suggestion_text(tools) if tools else None

        if tools:
            items = [(t.get("name", "?"), f"{t.get('score', 0):.2f}") for t in tools]
            rich.print(f"[cyan]Suggested tools: {items}[/cyan]")

        # Update system message (removes old suggestions even if no new ones)
        new_system = self._update_system_message(request.system_message, suggestion)
        return request.override(system_message=new_system)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Search tools and inject suggestions (sync)."""
        request = self._process_request(request)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Search tools and inject suggestions (async)."""
        request = self._process_request(request)
        return await handler(request)
