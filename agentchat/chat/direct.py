"""Direct mode chat loop with dynamic tool discovery."""

from typing import Any, cast
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from prompt_toolkit import PromptSession

from ..agent import DirectModeAgentFactory
from ..middleware import DynamicToolMiddleware
from ..ui import (
    console,
    print_error,
    print_info,
    print_streaming_end,
    print_streaming_start,
    print_welcome,
)
from .common import create_key_bindings, process_stream_events


async def stream_with_tool_discovery(
    factory: DirectModeAgentFactory,
    agent: CompiledStateGraph[Any],
    input_or_command: dict[str, Any] | Command[Any],
    config: RunnableConfig,
) -> bool:
    """Stream agent and handle tool discovery interrupts recursively.

    Args:
        factory: Agent factory for creating new agents.
        agent: Current agent instance.
        input_or_command: Input message or resume command.
        config: Runnable config with thread_id.

    Returns:
        True if interrupted, False otherwise.
    """
    interrupted = await process_stream_events(
        agent.astream_events(input_or_command, config=config, version="v2")
    )

    if interrupted:
        return True

    state = agent.get_state(config)

    if not (state.next and state.tasks):
        return False

    for task in state.tasks:
        for intr in task.interrupts:
            if intr.value.get("type") == DynamicToolMiddleware.INTERRUPT_TYPE:
                discovered = intr.value.get("discovered_tools", [])
                print_info(f"Discovered tools: {discovered}")

                # Recreate agent with discovered tools and resume
                new_agent = factory.create_agent(set(discovered))
                return await stream_with_tool_discovery(factory, new_agent, Command(resume={}), config)

    return False


async def direct_chat_loop() -> None:
    """Run the direct mode chat loop with dynamic tool discovery."""
    load_dotenv()
    print_welcome("direct")

    # Create agent factory
    factory = DirectModeAgentFactory()
    exit_stack = await factory.initialize()

    # Create initial agent (only tool_search)
    agent = factory.create_agent()

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

                interrupted = await stream_with_tool_discovery(
                    factory,
                    agent,
                    {"messages": [{"role": "user", "content": user_input}]},
                    config,
                )

                print_streaming_end()
                console.print()

                # Update agent with any newly discovered tools
                agent = factory.create_agent(factory.middleware.discovered_tools)

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
