"""Direct mode chat loop with dynamic tool discovery."""

from typing import Any, NotRequired, TypedDict, cast
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from prompt_toolkit import PromptSession

from ..agent import DirectModeAgentFactory
from ..middleware import DynamicToolMiddleware
from ..resume import (
    _extract_tools_from_messages,
    aget_messages,
    aselect_thread_interactive,
    print_recent_messages,
)
from ..ui import (
    console,
    print_error,
    print_hitl_request,
    print_info,
    print_streaming_end,
    print_streaming_start,
    print_welcome,
)
from .common import create_key_bindings, process_stream_events


class HITLToolConfig(TypedDict):
    """Configuration for a HITL tool."""

    auto_approve: NotRequired[tuple[str, ...]]  # Args to use as key for auto-approval (omit to disable)


# Tools that require human approval before execution
HITL_TOOLS: dict[str, HITLToolConfig] = {
    "send_email": {"auto_approve": ("to",)},  # Auto-approve if same recipient
    "create_calendar_event": {},  # Always require approval
}


def make_approval_key(action: dict[str, Any]) -> tuple[str, ...] | None:
    """Create approval key from action for auto-approve lookup.

    Args:
        action: Action request with "name" and "args" keys.

    Returns:
        Tuple key for approved_calls set, or None if auto-approve is disabled.
    """
    name = action.get("name", "")
    config = HITL_TOOLS.get(name, {})
    auto_approve_args = config.get("auto_approve")

    if auto_approve_args is None:
        return None  # Auto-approve disabled for this tool

    args = action.get("args", {})
    return (name,) + tuple(str(args.get(k, "")) for k in auto_approve_args)


async def prompt_hitl_decisions(
    action_requests: list[dict[str, Any]],
    session: PromptSession[str],
    approved_calls: set[tuple[str, ...]],
) -> list[dict[str, Any]]:
    """Prompt user for HITL decisions, with auto-approve for known calls.

    Args:
        action_requests: List of action requests from interrupt.
        session: Prompt session for user input.
        approved_calls: Set of previously approved call keys.

    Returns:
        List of decisions (approve or reject).
    """
    decisions: list[dict[str, Any]] = []

    for action in action_requests:
        key = make_approval_key(action)

        # Auto-approve if previously approved
        if key is not None and key in approved_calls:
            print_info(f"Auto-approved: {action.get('name', 'unknown')}")
            decisions.append({"type": "approve"})
            continue

        # Prompt user
        print_hitl_request(action)
        response = await session.prompt_async("Approve? (y/n): ")
        response = response.strip().lower()

        if response in ("y", "yes"):
            decisions.append({"type": "approve"})
            # Remember for auto-approve (if enabled for this tool)
            if key is not None:
                approved_calls.add(key)
        else:
            decisions.append({"type": "reject", "message": "User rejected"})

    return decisions


async def stream_with_tool_discovery(
    factory: DirectModeAgentFactory,
    agent: CompiledStateGraph[Any],
    input_or_command: dict[str, Any] | Command[Any],
    config: RunnableConfig,
    session: PromptSession[str],
    approved_calls: set[tuple[str, ...]],
) -> bool:
    """Stream agent and handle tool discovery/HITL interrupts recursively.

    Args:
        factory: Agent factory for creating new agents.
        agent: Current agent instance.
        input_or_command: Input message or resume command.
        config: Runnable config with thread_id.
        session: Prompt session for user input.
        approved_calls: Set of previously approved call keys for auto-approve.

    Returns:
        True if interrupted, False otherwise.
    """
    interrupted = await process_stream_events(agent.astream_events(input_or_command, config=config, version="v2"))

    if interrupted:
        return True

    state = await agent.aget_state(config)

    if not (state.next and state.tasks):
        return False

    for task in state.tasks:
        for intr in task.interrupts:
            # Handle tool discovery interrupts
            if intr.value.get("type") == DynamicToolMiddleware.INTERRUPT_TYPE:
                discovered = intr.value.get("discovered_tools", [])
                print_info(f"Discovered tools: {discovered}")

                # Recreate agent with discovered tools and resume
                new_agent = factory.create_agent(set(discovered))
                return await stream_with_tool_discovery(
                    factory, new_agent, Command(resume={}), config, session, approved_calls
                )

            # Handle HITL interrupts
            if "action_requests" in intr.value:
                action_requests = intr.value["action_requests"]
                decisions = await prompt_hitl_decisions(action_requests, session, approved_calls)

                print_streaming_start()
                return await stream_with_tool_discovery(
                    factory, agent, Command(resume={"decisions": decisions}), config, session, approved_calls
                )

    return False


async def direct_chat_loop(resume: bool = False) -> None:
    """Run the direct mode chat loop with dynamic tool discovery.

    Args:
        resume: Whether to show thread selection for resuming.
    """
    load_dotenv()
    print_welcome("direct")

    # Create agent factory with HITL tools
    factory = DirectModeAgentFactory(hitl_tools=set(HITL_TOOLS.keys()))
    exit_stack = await factory.initialize()

    # Select thread if resuming
    thread_id: str | None = None
    if resume and factory.checkpointer is not None:
        thread_id = await aselect_thread_interactive(factory.checkpointer)

    # Restore discovered tools and messages if resuming
    restored_tools: set[str] = set()
    restored_messages: list[Any] = []
    if thread_id is not None and factory.checkpointer is not None:
        restored_messages = await aget_messages(thread_id, factory.checkpointer)
        restored_tools = _extract_tools_from_messages(restored_messages)
        factory.middleware.discovered_tools = restored_tools

    # Create agent with restored tools (or just tool_search for new sessions)
    agent = factory.create_agent(restored_tools or None)

    if thread_id is None:
        thread_id = str(uuid4())
        print_info(f"New session: {thread_id[:8]}...")
    else:
        if restored_tools:
            print_info(f"Resuming session: {thread_id[:8]}... (tools: {', '.join(restored_tools)})")
        else:
            print_info(f"Resuming session: {thread_id[:8]}...")
        # Show recent conversation
        print_recent_messages(restored_messages, console)
    console.print()

    config = cast(RunnableConfig, {"configurable": {"thread_id": thread_id}})
    session: PromptSession[str] = PromptSession(key_bindings=create_key_bindings())

    # Track approved calls for auto-approve (in-memory only)
    approved_calls: set[tuple[str, ...]] = set()

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
                    session,
                    approved_calls,
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
