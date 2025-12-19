"""Agent Chat - CLI chat application with tool search and programmatic tool calling."""

import argparse
import asyncio
import os

# Suppress warnings before importing libraries that trigger them
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")  # HuggingFace tokenizers fork warning
os.environ.setdefault("LANCEDB_LOG", "error")  # LanceDB "No existing dataset" warning

from .chat import direct_chat_loop, programmatic_chat_loop  # noqa: E402
from .ui import print_info  # noqa: E402

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
