"""Agent Chat - CLI chat application with tool search and programmatic tool calling."""

import asyncio

from .chat import direct_chat_loop, programmatic_chat_loop
from .ui import print_info

__version__ = "0.1.0"


def main_direct() -> None:
    """Entry point for direct mode CLI."""
    try:
        asyncio.run(direct_chat_loop())
    except KeyboardInterrupt:
        print_info("\nGoodbye!")


def main_programmatic() -> None:
    """Entry point for programmatic mode CLI."""
    try:
        asyncio.run(programmatic_chat_loop())
    except KeyboardInterrupt:
        print_info("\nGoodbye!")
