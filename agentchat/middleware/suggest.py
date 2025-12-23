"""Unified suggestion middleware for automatic recommendations."""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

import rich
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import HumanMessage, SystemMessage

from ..tools.embeddings import SearchableIndex


@dataclass
class IndexConfig:
    """Configuration for a searchable index in the suggestion middleware."""

    index: SearchableIndex
    label: str  # e.g., "tools", "skills"
    marker_name: str  # e.g., "TOOL_SUGGESTIONS", "SKILL_SUGGESTIONS"
    usage_hint: str | None = None  # e.g., "Use tool_search_regex('^name$') to enable these tools."
    format_item: Callable[[dict[str, Any]], str] = (
        lambda item: f"- {item.get('name', '?')}: {item.get('description', '')}"
    )

    @property
    def suggest_start(self) -> str:
        return f"[{self.marker_name}]"

    @property
    def suggest_end(self) -> str:
        return f"[/{self.marker_name}]"


class SuggestMiddleware(AgentMiddleware[AgentState[Any], Any]):
    """Middleware that suggests relevant items from multiple indexes.

    Searches multiple indexes for items matching the latest user message
    and injects suggestions into the system prompt before model call.
    """

    def __init__(self, indexes: list[IndexConfig], top_k: int = 3):
        """Initialize middleware.

        Args:
            indexes: List of index configurations.
            top_k: Number of items to suggest per index.
        """
        self.indexes = indexes
        self.top_k = top_k
        self._index_available: dict[str, bool | None] = {cfg.label: None for cfg in indexes}
        self._last_user_message: str | None = None

    def _get_latest_user_message(self, messages: Sequence[Any]) -> str | None:
        """Extract the latest user message content."""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                content = msg.content
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text = item.get("text")
                            if isinstance(text, str):
                                return text
        return None

    async def _search_index(self, config: IndexConfig, query: str) -> list[dict[str, Any]]:
        """Search a single index. Returns empty list on failure."""
        if self._index_available.get(config.label) is False:
            return []

        try:
            results = await config.index.search(query, self.top_k)
            self._index_available[config.label] = True
            return results
        except Exception as e:  # noqa: BLE001
            if self._index_available.get(config.label) is None:
                rich.print(f"[yellow]Warning: {config.label} search failed: {e}[/yellow]")
            self._index_available[config.label] = False
            return []

    def _build_suggestion_text(self, config: IndexConfig, items: list[dict[str, Any]]) -> str:
        """Build suggestion text for a single index."""
        if not items:
            return ""

        lines = [config.suggest_start]
        lines.append(f"Suggested {config.label} based on user's request:")
        for item in items:
            lines.append(config.format_item(item))
        if config.usage_hint:
            lines.append(config.usage_hint)
        lines.append(config.suggest_end)

        return "\n".join(lines)

    def _remove_old_suggestions(self, content: str) -> str:
        """Remove all existing suggestion blocks from content."""
        for config in self.indexes:
            start_idx = content.find(config.suggest_start)
            if start_idx == -1:
                continue

            end_idx = content.find(config.suggest_end)
            if end_idx == -1:
                continue

            end_idx += len(config.suggest_end)
            before = content[:start_idx].rstrip()
            after = content[end_idx:].lstrip()

            if before and after:
                content = f"{before}\n\n{after}"
            else:
                content = before or after

        return content

    def _update_system_message(
        self, system_message: SystemMessage | None, suggestions: list[str]
    ) -> SystemMessage | None:
        """Update system message with suggestions."""
        suggestion_text = "\n\n".join(s for s in suggestions if s)

        if system_message is None:
            if suggestion_text:
                return SystemMessage(content=suggestion_text)
            return None

        content = (
            system_message.content
            if isinstance(system_message.content, str)
            else str(system_message.content)
        )
        clean_content = self._remove_old_suggestions(content)

        if suggestion_text:
            new_content = f"{clean_content}\n\n{suggestion_text}"
        else:
            new_content = clean_content

        return SystemMessage(
            content=new_content,
            additional_kwargs=system_message.additional_kwargs,
            response_metadata=system_message.response_metadata,
            id=system_message.id,
        )

    async def _process_request(self, request: ModelRequest) -> ModelRequest:
        """Process request: search all indexes and update system message."""
        user_msg = self._get_latest_user_message(request.messages)
        if not user_msg:
            return request

        if user_msg == self._last_user_message:
            return request

        self._last_user_message = user_msg

        # Search all indexes
        suggestions: list[str] = []
        for config in self.indexes:
            items = await self._search_index(config, user_msg)
            if items:
                log_items = [(item.get("name", "?"), f"{item.get('score', 0):.2f}") for item in items]
                rich.print(f"[cyan]Suggested {config.label}: {log_items}[/cyan]")
                suggestions.append(self._build_suggestion_text(config, items))

        new_system = self._update_system_message(request.system_message, suggestions)
        return request.override(system_message=new_system)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Search and inject suggestions (async)."""
        request = await self._process_request(request)
        return await handler(request)
