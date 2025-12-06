"""Sandboxed code execution tool using sandbox-runtime (srt)."""

import asyncio
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import BaseTool, tool

# Lazy-initialized srt command
_srt_cmd: list[str] | None = None
_srt_checked: bool = False


def _get_srt_cmd() -> list[str] | None:
    """Get the srt command, checking lazily on first call."""
    global _srt_cmd, _srt_checked
    if not _srt_checked:
        if shutil.which("srt"):
            _srt_cmd = ["srt"]
        elif shutil.which("npx"):
            _srt_cmd = ["npx", "@anthropic-ai/sandbox-runtime"]
        _srt_checked = True
    return _srt_cmd


def is_srt_available() -> bool:
    """Check if sandbox-runtime is available."""
    return _get_srt_cmd() is not None


def create_execute_code_tool(
    registry: dict[str, BaseTool],
    *,
    srt_settings: str | Path | None = None,
) -> BaseTool:
    """Create a sandboxed code execution tool.

    Args:
        registry: Tool registry for resolving tool calls.
        srt_settings: Optional path to srt settings file for network/filesystem
            permissions. See https://github.com/anthropic-experimental/sandbox-runtime

    Returns:
        A tool that executes Python code in a sandbox with tool_call support.

    Raises:
        RuntimeError: If sandbox-runtime is not available.
    """
    srt_cmd = _get_srt_cmd()
    if srt_cmd is None:
        raise RuntimeError(
            "sandbox-runtime (srt) not available. "
            "Install globally with 'npm install -g @anthropic-ai/sandbox-runtime' "
            "or ensure npx is available."
        )

    # Add settings flag if provided
    if srt_settings is not None:
        srt_cmd = [*srt_cmd, "--settings", str(srt_settings)]

    @tool
    async def execute_code(code: str) -> str:
        """Execute async Python code in a secure sandbox.

        Available functions:
        - await tool_call(name, **kwargs): Call a registered tool, returns dict
        - print(): Output results (only printed text is returned)

        The code runs in an isolated environment with no filesystem or network access.
        Communication uses JSON-RPC 2.0 protocol over stdout/stdin.

        Example:
            sales = await tool_call("query_sales", region="west")
            weather = await tool_call("get_weather", city="Tokyo")
            print(f"Revenue: ${sales['revenue']}, Weather: {weather['condition']}")

        Args:
            code: Async Python code to execute. Use 'await tool_call(name, **kwargs)'
                  to call tools and 'print()' to output results.

        Returns:
            The printed output from the code, or error message if execution fails.
        """
        # Indent user code for async main()
        indented_code = "\n".join("    " + line for line in code.split("\n"))

        # JSON-RPC 2.0 wrapper
        wrapper = f'''
import asyncio
import json
import sys

_request_id = 0

async def tool_call(name, **kwargs):
    """Call a tool on the host via JSON-RPC 2.0."""
    global _request_id
    _request_id += 1
    request = {{
        "jsonrpc": "2.0",
        "method": name,
        "params": kwargs,
        "id": _request_id
    }}
    sys.stdout.write(json.dumps(request) + "\\n")
    sys.stdout.flush()
    response = json.loads(sys.stdin.readline().strip())
    if "error" in response:
        raise Exception(f"Tool error: {{response['error']['message']}}")
    return response["result"]

_original_print = print
def print(*args, **kwargs):
    """Print via JSON-RPC 2.0 notification."""
    import io
    buf = io.StringIO()
    kwargs["file"] = buf
    _original_print(*args, **kwargs)
    text = buf.getvalue()
    notification = {{
        "jsonrpc": "2.0",
        "method": "print",
        "params": {{"text": text}}
    }}
    sys.stdout.write(json.dumps(notification) + "\\n")
    sys.stdout.flush()

async def main():
{indented_code}

asyncio.run(main())
'''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(wrapper)
            script_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                *srt_cmd,
                "python",
                "-u",
                script_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            assert proc.stdin is not None
            assert proc.stdout is not None
            assert proc.stderr is not None

            proc_stdin = proc.stdin
            proc_stdout = proc.stdout
            proc_stderr = proc.stderr

            output_lines: list[str] = []

            timed_out = False
            while True:
                try:
                    line_bytes = await asyncio.wait_for(proc_stdout.readline(), timeout=30)
                except TimeoutError:
                    timed_out = True
                    break

                if not line_bytes:
                    break

                line = line_bytes.decode().strip()
                if not line:
                    continue

                # Parse JSON-RPC message
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Check if notification (no id) or request (has id)
                if "id" not in msg:
                    # Notification: handle print
                    if msg.get("method") == "print":
                        output_lines.append(msg["params"]["text"])
                else:
                    # Request: tool call
                    request_id = msg["id"]
                    tool_name = msg["method"]
                    tool_kwargs = msg.get("params", {})

                    if tool_name in registry:
                        tool_obj = registry[tool_name]
                        # Use ainvoke for async tools (like MCP tools)
                        if hasattr(tool_obj, "coroutine") and tool_obj.coroutine is not None:
                            raw_result = await tool_obj.ainvoke(tool_kwargs)
                        else:
                            raw_result = tool_obj.invoke(tool_kwargs)

                        # MCP tools may return JSON strings - parse if needed
                        if isinstance(raw_result, str):
                            try:
                                call_result = json.loads(raw_result)
                            except json.JSONDecodeError:
                                call_result = raw_result
                        else:
                            call_result = raw_result

                        response = {
                            "jsonrpc": "2.0",
                            "result": call_result,
                            "id": request_id,
                        }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
                            "id": request_id,
                        }

                    proc_stdin.write((json.dumps(response) + "\n").encode())
                    await proc_stdin.drain()

            # Kill process if timed out
            if timed_out:
                proc.kill()
                await proc.wait()
                return "Error: Execution timed out (30s limit)"

            stderr_bytes = await proc_stderr.read()
            stderr = stderr_bytes.decode()
            await proc.wait()

            output = "".join(output_lines)
            if stderr:
                output += f"\nStderr: {stderr}"
            if proc.returncode != 0:
                output += f"\nExit code: {proc.returncode}"

            return output.strip() if output.strip() else "Code executed successfully (no output)"

        except TimeoutError:
            proc.kill()
            await proc.wait()
            return "Error: Execution timed out (30s limit)"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"
        finally:
            Path(script_path).unlink(missing_ok=True)

    return execute_code
