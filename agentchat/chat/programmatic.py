"""Programmatic mode chat loop with sandbox execution."""

import sys
from typing import cast
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from prompt_toolkit import PromptSession

from ..agent import create_programmatic_agent
from ..ui import (
    console,
    print_error,
    print_info,
    print_streaming_end,
    print_streaming_start,
    print_welcome,
)
from .common import create_key_bindings, process_stream_events


async def programmatic_chat_loop() -> None:
    """Run the programmatic mode chat loop."""
    load_dotenv()
    print_welcome("programmatic")

    try:
        agent, exit_stack = await create_programmatic_agent()
    except RuntimeError as e:
        print_error(str(e))
        sys.exit(1)

    thread_id = str(uuid4())
    print_info(f"Session: {thread_id[:8]}...")
    console.print()

    config = cast(RunnableConfig, {"configurable": {"thread_id": thread_id}})
    session: PromptSession[str] = PromptSession(key_bindings=create_key_bindings())

    async with exit_stack:
        while True:
            try:
                user_input = await session.prompt_async("> ", multiline=True)
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() == "/exit":
                    print_info("Goodbye!")
                    break

                console.print()
                print_streaming_start()

                interrupted = await process_stream_events(
                    agent.astream_events(
                        {"messages": [{"role": "user", "content": user_input}]},
                        config=config,
                        version="v2",
                    )
                )

                print_streaming_end()
                console.print()

                if interrupted:
                    console.print("[dim]Interrupted[/dim]")
                    console.print()
                    continue

            except KeyboardInterrupt:
                print_info("\nGoodbye!")
                break
            except EOFError:
                print_info("\nGoodbye!")
                break
            except Exception as e:
                print_streaming_end()
                print_error(f"{type(e).__name__}: {e}")
                console.print()
