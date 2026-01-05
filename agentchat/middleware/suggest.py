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
    label: str  # e.g., "tool", "skill" - used as prefix like [tool]
    usage_hint: str | None = None  # e.g., "Use tool_search_regex('^name$') to enable tools."


_SUGGEST_START = "[SUGGESTIONS]"
_SUGGEST_END = "[/SUGGESTIONS]"


class SuggestMiddleware(AgentMiddleware[AgentState[Any], Any]):
    """Middleware that suggests relevant items from multiple indexes.

    Searches multiple indexes for items matching the latest user message,
    merges results by score, and injects top-k suggestions into the system prompt.
    """

    def __init__(self, indexes: list[IndexConfig], top_k: int = 5):
        """Initialize middleware.

        Args:
            indexes: List of index configurations.
            top_k: Total number of items to suggest across all indexes.
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

    async def _search_index(
        self, config: IndexConfig, query: str, limit: int
    ) -> list[tuple[IndexConfig, dict[str, Any]]]:
        """Search a single index. Returns list of (config, item) tuples."""
        if self._index_available.get(config.label) is False:
            return []

        try:
            results = await config.index.search(query, limit)
            self._index_available[config.label] = True
            return [(config, item) for item in results]
        except Exception as e:  # noqa: BLE001
            if self._index_available.get(config.label) is None:
                rich.print(f"[yellow]Warning: {config.label} search failed: {e}[/yellow]")
            self._index_available[config.label] = False
            return []

    def _build_suggestion_text(
        self, items: list[tuple[IndexConfig, dict[str, Any]]]
    ) -> str:
        """Build unified suggestion text from merged results."""
        if not items:
            return ""

        lines = [_SUGGEST_START, "Suggested items based on user's request:"]

        # Track which labels appear in results
        labels_used: set[str] = set()

        for config, item in items:
            labels_used.add(config.label)
            name = item.get("name", "?")
            desc = item.get("description", "")
            lines.append(f"- [{config.label}] {name}: {desc}")

        # Add hints for labels that appear in results
        lines.append("")
        for config in self.indexes:
            if config.label in labels_used and config.usage_hint:
                lines.append(config.usage_hint)

        lines.append(_SUGGEST_END)
        return "\n".join(lines)

    def _remove_old_suggestions(self, content: str) -> str:
        """Remove existing suggestion block from content."""
        start_idx = content.find(_SUGGEST_START)
        if start_idx == -1:
            return content

        end_idx = content.find(_SUGGEST_END)
        if end_idx == -1:
            return content

        end_idx += len(_SUGGEST_END)
        before = content[:start_idx].rstrip()
        after = content[end_idx:].lstrip()

        if before and after:
            return f"{before}\n\n{after}"
        return before or after

    def _update_system_message(
        self, system_message: SystemMessage | None, suggestion_text: str
    ) -> SystemMessage | None:
        """Update system message with suggestions."""
        if system_message is None:
            if suggestion_text:
                return SystemMessage(content=suggestion_text)
            return None

        content = system_message.content if isinstance(system_message.content, str) else str(system_message.content)
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
        """Process request: search all indexes, merge by score, update system message."""
        user_msg = self._get_latest_user_message(request.messages)
        if not user_msg:
            return request

        if user_msg == self._last_user_message:
            return request

        self._last_user_message = user_msg

        # Search all indexes and collect results
        all_results: list[tuple[IndexConfig, dict[str, Any]]] = []
        for config in self.indexes:
            results = await self._search_index(config, user_msg, self.top_k)
            all_results.extend(results)

        # Sort by score (higher is better) and take top-k
        all_results.sort(key=lambda x: x[1].get("score", 0), reverse=True)
        top_items = all_results[: self.top_k]

        if top_items:
            log_items = [
                (f"[{cfg.label}] {item.get('name', '?')}", f"{item.get('score', 0):.2f}")
                for cfg, item in top_items
            ]
            rich.print(f"[cyan]Suggestions: {log_items}[/cyan]")

        suggestion_text = self._build_suggestion_text(top_items)
        new_system = self._update_system_message(request.system_message, suggestion_text)
        return request.override(system_message=new_system)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Search and inject suggestions (async)."""
        request = await self._process_request(request)
        return await handler(request)
