#!/usr/bin/env python3
"""Dump checkpoint messages from SQLite database as JSON."""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

DEFAULT_DB = Path(__file__).parent.parent / "tmp" / "checkpoints.db"


def message_to_dict(msg: Any) -> dict[str, Any]:
    """Convert a message object to a JSON-serializable dict."""
    result: dict[str, Any] = {
        "type": type(msg).__name__,
        "content": msg.content,
    }
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        result["tool_calls"] = msg.tool_calls
    if hasattr(msg, "tool_call_id") and msg.tool_call_id:
        result["tool_call_id"] = msg.tool_call_id
    if hasattr(msg, "name") and msg.name:
        result["name"] = msg.name
    return result


def dump_checkpoint(
    db_path: Path, thread_id: str | None = None, limit: int = 1
) -> list[dict[str, Any]]:
    """Dump checkpoints as JSON-serializable dicts."""
    if not db_path.exists():
        return []

    serde = JsonPlusSerializer()
    conn = sqlite3.connect(db_path)

    query = "SELECT thread_id, checkpoint_id, checkpoint FROM checkpoints"
    params: list[str] = []

    if thread_id:
        query += " WHERE thread_id = ?"
        params.append(thread_id)

    query += " ORDER BY checkpoint_id DESC LIMIT ?"
    params.append(str(limit))

    cursor = conn.execute(query, params)
    results: list[dict[str, Any]] = []

    for row in cursor:
        tid, cid, checkpoint_blob = row
        data = serde.loads_typed(("msgpack", checkpoint_blob))
        messages = data.get("channel_values", {}).get("messages", [])

        results.append({
            "thread_id": tid,
            "checkpoint_id": cid,
            "messages": [message_to_dict(m) for m in messages],
        })

    return results


def list_threads(db_path: Path) -> list[dict[str, Any]]:
    """List all threads in database."""
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT thread_id, COUNT(*) as count, MAX(checkpoint_id) as latest "
        "FROM checkpoints GROUP BY thread_id ORDER BY latest DESC"
    )

    return [
        {"thread_id": tid, "checkpoint_count": count, "latest_checkpoint": latest}
        for tid, count, latest in cursor
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump checkpoint messages as JSON")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Database path")
    parser.add_argument("--thread", "-t", type=str, help="Filter by thread ID")
    parser.add_argument("--limit", "-n", type=int, default=1, help="Number of checkpoints")
    parser.add_argument("--list", "-l", action="store_true", help="List threads")

    args = parser.parse_args()

    if args.list:
        data = list_threads(args.db)
    else:
        data = dump_checkpoint(args.db, args.thread, args.limit)

    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
