"""Common utilities for chat loops."""

from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessageChunk
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from ..ui import (
    print_code_execution,
    print_streaming_end,
    print_streaming_start,
    print_streaming_token,
    print_tool_call,
    print_tool_result,
)


def create_key_bindings() -> KeyBindings:
    """Create key bindings for the prompt.

    - Ctrl+J or Alt+Enter: Submit
    - Enter: New line
    - Ctrl+D: Exit
    """
    kb = KeyBindings()

    @kb.add("c-j")  # Ctrl+J to submit
    @kb.add(Keys.Escape, Keys.Enter)  # Alt+Enter to submit
    def _(event: Any) -> None:
        event.current_buffer.validate_and_handle()

    @kb.add(Keys.Enter)
    def _(event: Any) -> None:
        event.current_buffer.insert_text("\n")

    @kb.add("c-d")  # Ctrl+D to exit
    def _(event: Any) -> None:
        event.app.exit(exception=EOFError)

    return kb


async def process_stream_events(
    event_stream: AsyncIterator[Any],
) -> bool:
    """Process streaming events from agent.

    Args:
        event_stream: Async iterator of events.

    Returns:
        True if interrupted by KeyboardInterrupt, False otherwise.
    """
    printed_tool_results: set[str] = set()

    try:
        async for event in event_stream:
            kind = event.get("event", "")
            data = event.get("data", {})

            if kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                if isinstance(chunk, AIMessageChunk):
                    # Handle text content
                    if isinstance(chunk.content, str) and chunk.content:
                        print_streaming_token(chunk.content)
                    elif isinstance(chunk.content, list):
                        for item in chunk.content:
                            if isinstance(item, dict):
                                if item.get("type") == "text":
                                    text = item.get("text", "")
                                    if text:
                                        print_streaming_token(text)

            elif kind == "on_tool_start":
                tool_name = event.get("name", "")
                tool_input: dict[str, Any] = data.get("input", {})

                # End streaming line before tool output
                print_streaming_end()

                if tool_name == "execute_code":
                    code = tool_input.get("code", "")
                    if code:
                        print_code_execution(code)
                else:
                    print_tool_call(tool_name, tool_input)

            elif kind == "on_tool_end":
                tool_name = event.get("name", "")
                output = data.get("output", "")
                run_id = event.get("run_id", "")

                if run_id not in printed_tool_results:
                    printed_tool_results.add(run_id)
                    if isinstance(output, str):
                        print_tool_result(tool_name, output)
                    else:
                        print_tool_result(tool_name, str(output))

                # Restart streaming indicator
                print_streaming_start()
    except KeyboardInterrupt:
        return True

    return False
