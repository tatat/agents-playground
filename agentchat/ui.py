"""UI formatting utilities using rich."""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


def print_welcome(mode: str = "programmatic") -> None:
    """Print welcome message.

    Args:
        mode: "programmatic" or "direct".
    """
    console.print()

    if mode == "programmatic":
        description = (
            "A CLI chat with tool search and programmatic tool calling.\n\n"
            "[dim]The agent can:[/dim]\n"
            "  - Search for tools with [cyan]tool_search_regex[/cyan]\n"
            "  - Execute code in sandbox with [cyan]execute_code[/cyan]"
        )
    else:
        description = (
            "A CLI chat with direct tool calling.\n\n"
            "[dim]The agent can:[/dim]\n"
            "  - Search for tools with [cyan]tool_search_regex[/cyan]\n"
            "  - Call tools directly (weather, sales, calendar, etc.)"
        )

    console.print(
        Panel(
            f"[bold blue]Agent Chat[/bold blue] [dim]({mode} mode)[/dim]\n\n"
            f"{description}\n\n"
            "[dim]Input:[/dim]\n"
            "  [cyan]Alt+Enter[/cyan] - Send message\n"
            "  [cyan]Enter[/cyan] - New line\n\n"
            "[dim]Commands:[/dim]\n"
            "  [cyan]/exit[/cyan] - Exit the chat\n"
            "  [cyan]Ctrl+C[/cyan] or [cyan]Ctrl+D[/cyan] - Exit the chat",
            title="Welcome",
            border_style="blue",
        )
    )
    console.print()


def print_user_message(content: str) -> None:
    """Print a user message.

    Args:
        content: The message content.
    """
    console.print(Panel(content, title="[bold green]You[/bold green]", border_style="green"))


def print_assistant_message(content: str) -> None:
    """Print an assistant message.

    Args:
        content: The message content.
    """
    console.print(
        Panel(
            Markdown(content),
            title="[bold blue]Assistant[/bold blue]",
            border_style="blue",
        )
    )


def print_tool_call(name: str, args: dict[str, Any]) -> None:
    """Print a tool call.

    Args:
        name: Tool name.
        args: Tool arguments.
    """
    # Filter out injected runtime argument
    filtered_args = {k: v for k, v in args.items() if k != "runtime"}
    args_str = ", ".join(f"{k}={v!r}" for k, v in filtered_args.items())
    console.print(f"[dim]  > Calling [cyan]{name}[/cyan]({args_str})[/dim]")


def print_tool_result(name: str, content: str) -> None:
    """Print a tool result.

    Args:
        name: Tool name.
        content: Result content.
    """
    # Truncate long results
    display_content = content[:500] + "..." if len(content) > 500 else content
    console.print(f"[dim]  < [cyan]{name}[/cyan]: {display_content}[/dim]")


def print_code_execution(code: str) -> None:
    """Print code being executed.

    Args:
        code: The Python code.
    """
    console.print(
        Panel(Syntax(code, "python", theme="monokai"), title="[yellow]Executing Code[/yellow]", border_style="yellow")
    )


def print_streaming_start() -> None:
    """Print indicator that streaming has started."""
    console.print("[bold blue]Assistant:[/bold blue] ", end="")


def print_streaming_token(token: str) -> None:
    """Print a streaming token.

    Args:
        token: The token to print.
    """
    console.print(token, end="", markup=False)


def print_streaming_end() -> None:
    """Print newline after streaming ends."""
    console.print()


def print_error(message: str) -> None:
    """Print an error message.

    Args:
        message: The error message.
    """
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_info(message: str) -> None:
    """Print an info message.

    Args:
        message: The info message.
    """
    console.print(f"[dim]{message}[/dim]")


def format_message(message: HumanMessage | AIMessage | ToolMessage) -> None:
    """Format and print a message based on its type.

    Args:
        message: The message to format.
    """
    if isinstance(message, HumanMessage):
        print_user_message(str(message.content))
    elif isinstance(message, AIMessage):
        content = message.content
        if isinstance(content, str) and content:
            print_assistant_message(content)
        elif isinstance(content, list):
            # Handle mixed content (text + tool calls)
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        if text:
                            print_assistant_message(text)
                    elif item.get("type") == "tool_use":
                        print_tool_call(item.get("name", "unknown"), item.get("input", {}))
    elif isinstance(message, ToolMessage):
        print_tool_result(message.name or "unknown", str(message.content))


def print_hitl_request(action: dict[str, Any]) -> None:
    """Print a HITL approval request.

    Args:
        action: Action request with "name" and "args" keys.
    """
    name = action.get("name", "unknown")
    args = action.get("args", {})
    args_str = "\n".join(f"  {k}: {v!r}" for k, v in args.items())

    console.print()
    console.print(
        Panel(
            f"[bold]{name}[/bold]\n\n{args_str}",
            title="[yellow]Approval Required[/yellow]",
            border_style="yellow",
        )
    )
