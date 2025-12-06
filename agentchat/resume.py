"""Thread selection for resuming conversations."""

from typing import TYPE_CHECKING, Any

from langchain_core.runnables import RunnableConfig
from prompt_toolkit import PromptSession
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver


def _extract_tools_from_messages(messages: list[Any]) -> set[str]:
    """Extract tool names from message list."""
    tools: set[str] = set()
    for msg in messages:
        if type(msg).__name__ == "ToolMessage":
            if hasattr(msg, "name") and msg.name:
                # Skip tool_search itself
                if msg.name != "tool_search":
                    tools.add(msg.name)
    return tools


def _get_first_human_message_preview(messages: list[Any]) -> str:
    """Get preview text from first HumanMessage."""
    for msg in messages:
        if type(msg).__name__ == "HumanMessage":
            content = msg.content
            if isinstance(content, str):
                return content[:50] + ("..." if len(content) > 50 else "")
    return ""


async def aget_discovered_tools(
    thread_id: str, checkpointer: "BaseCheckpointSaver[Any]"
) -> set[str]:
    """Extract tool names used in a thread from checkpointer.

    Args:
        thread_id: The thread ID to get tools for.
        checkpointer: The checkpointer to query.

    Returns:
        Set of tool names that were used in the thread.
    """
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    checkpoint_tuple = await checkpointer.aget_tuple(config)

    if not checkpoint_tuple:
        return set()

    messages = checkpoint_tuple.checkpoint.get("channel_values", {}).get("messages", [])
    return _extract_tools_from_messages(messages)


async def aget_thread_summaries(
    checkpointer: "BaseCheckpointSaver[Any]",
) -> list[dict[str, Any]]:
    """Get thread summaries with first user message preview.

    Args:
        checkpointer: The checkpointer to query.

    Returns:
        List of thread info dicts with thread_id, message_count, and preview.
    """
    results: list[dict[str, Any]] = []
    seen_threads: set[str] = set()

    # alist returns checkpoints in descending order by default
    # Pass None to list all threads (empty dict requires 'configurable' key)
    async for checkpoint_tuple in checkpointer.alist(None):
        thread_id = checkpoint_tuple.config.get("configurable", {}).get("thread_id")
        if not thread_id or thread_id in seen_threads:
            continue

        seen_threads.add(thread_id)
        messages = checkpoint_tuple.checkpoint.get("channel_values", {}).get("messages", [])

        results.append({
            "thread_id": thread_id,
            "message_count": len(messages),
            "preview": _get_first_human_message_preview(messages),
        })

    return results


async def aselect_thread_interactive(
    checkpointer: "BaseCheckpointSaver[Any]",
    console: Console | None = None,
) -> str | None:
    """Interactive thread selection UI.

    Args:
        checkpointer: The checkpointer to query for threads.
        console: Rich console for output. Created if not provided.

    Returns:
        Selected thread_id, or None for new session.
    """
    if console is None:
        console = Console()

    threads = await aget_thread_summaries(checkpointer)

    if not threads:
        console.print("[dim]No saved threads found. Starting new session.[/dim]")
        return None

    # Display thread table
    table = Table(title="Available Threads", show_header=True)
    table.add_column("#", style="cyan", width=3)
    table.add_column("Thread ID", style="green")
    table.add_column("Messages", justify="right")
    table.add_column("Preview", style="dim")

    for i, thread in enumerate(threads, 1):
        table.add_row(
            str(i),
            thread["thread_id"][:8] + "...",
            str(thread["message_count"]),
            thread["preview"] or "(empty)",
        )

    console.print(table)
    console.print()

    # Prompt for selection
    session: PromptSession[str] = PromptSession()
    while True:
        try:
            response = await session.prompt_async(
                f"Select thread (1-{len(threads)}) or 'n' for new: "
            )
            response = response.strip().lower()

            if response == "n":
                return None

            try:
                idx = int(response)
                if 1 <= idx <= len(threads):
                    selected = threads[idx - 1]
                    thread_id: str = selected["thread_id"]
                    console.print(f"[green]Resuming thread {thread_id[:8]}...[/green]")
                    return thread_id
                else:
                    console.print(f"[red]Please enter 1-{len(threads)} or 'n'[/red]")
            except ValueError:
                console.print("[red]Invalid input[/red]")

        except (KeyboardInterrupt, EOFError):
            return None
