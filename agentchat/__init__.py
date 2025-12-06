"""Agent Chat - CLI chat application with tool search and programmatic tool calling."""

import argparse
import asyncio

from .chat import direct_chat_loop, programmatic_chat_loop
from .ui import print_info

__version__ = "0.1.0"


def main_direct() -> None:
    """Entry point for direct mode CLI."""
    parser = argparse.ArgumentParser(description="Direct mode agent chat")
    parser.add_argument("--resume", "-r", action="store_true", help="Resume existing thread")
    args = parser.parse_args()

    try:
        asyncio.run(direct_chat_loop(resume=args.resume))
    except KeyboardInterrupt:
        print_info("\nGoodbye!")


def main_programmatic() -> None:
    """Entry point for programmatic mode CLI."""
    parser = argparse.ArgumentParser(description="Programmatic mode agent chat")
    parser.add_argument("--resume", "-r", action="store_true", help="Resume existing thread")
    args = parser.parse_args()

    try:
        asyncio.run(programmatic_chat_loop(resume=args.resume))
    except KeyboardInterrupt:
        print_info("\nGoodbye!")
