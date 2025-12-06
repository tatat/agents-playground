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


def create_execute_code_tool(registry: dict[str, BaseTool]) -> BaseTool:
    """Create a sandboxed code execution tool.

    Args:
        registry: Tool registry for resolving tool calls.

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

    @tool
    async def execute_code(code: str) -> str:
        """Execute async Python code in a secure sandbox.

        Available functions:
        - await tool_call(name, **kwargs): Call a registered tool, returns dict
        - print(): Output results (only printed text is returned)

        The code runs in an isolated environment with no filesystem or network access.

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

        wrapper = f'''
import asyncio
import json
import sys

async def tool_call(name, **kwargs):
    """Call a tool on the host via stdout/stdin protocol."""
    request = {{"name": name, "kwargs": kwargs}}
    sys.stdout.write(f"__TOOL_REQUEST__{{json.dumps(request)}}__END_REQUEST__\\n")
    sys.stdout.flush()
    response_line = sys.stdin.readline().strip()
    return json.loads(response_line)

_output_lines = []
_original_print = print
def print(*args, **kwargs):
    import io
    buf = io.StringIO()
    kwargs["file"] = buf
    _original_print(*args, **kwargs)
    _output_lines.append(buf.getvalue())

async def main():
{indented_code}

asyncio.run(main())

sys.stdout.write("__USER_OUTPUT__\\n")
sys.stdout.flush()
for line in _output_lines:
    sys.stdout.write(line)
sys.stdout.flush()
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
            user_output_started = False

            while True:
                try:
                    line_bytes = await asyncio.wait_for(proc_stdout.readline(), timeout=30)
                except TimeoutError:
                    break

                if not line_bytes:
                    break

                line = line_bytes.decode()

                if "__TOOL_REQUEST__" in line:
                    start = line.index("__TOOL_REQUEST__") + len("__TOOL_REQUEST__")
                    end = line.index("__END_REQUEST__")
                    request = json.loads(line[start:end])

                    tool_name = request["name"]
                    tool_kwargs = request["kwargs"]

                    if tool_name in registry:
                        tool_obj = registry[tool_name]
                        # Use ainvoke for async tools (like MCP tools)
                        if hasattr(tool_obj, "coroutine") and tool_obj.coroutine is not None:
                            call_result = await tool_obj.ainvoke(tool_kwargs)
                        else:
                            call_result = tool_obj.invoke(tool_kwargs)
                    else:
                        call_result = {"error": f"Unknown tool: {tool_name}"}

                    proc_stdin.write((json.dumps(call_result) + "\n").encode())
                    await proc_stdin.drain()
                elif "__USER_OUTPUT__" in line:
                    user_output_started = True
                elif user_output_started:
                    output_lines.append(line)

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
            return "Error: Execution timed out (30s limit)"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"
        finally:
            Path(script_path).unlink(missing_ok=True)

    return execute_code
