import ast
import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

_BLOCKED_IMPORTS = frozenset({
    "os", "sys", "subprocess", "shutil", "pathlib", "socket",
    "http", "urllib", "requests", "httpx", "ftplib", "smtplib",
    "multiprocessing", "threading", "ctypes", "importlib",
    "pickle", "shelve", "marshal", "builtins",
})

_BLOCKED_BUILTINS = frozenset({"open", "exec", "eval", "compile", "__import__"})


def _check_ast(code: str) -> Optional[str]:
    """Parse code with AST and return an error message if disallowed constructs are found."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"SyntaxError: {e}"

    for node in ast.walk(tree):
        # Block import statements for disallowed modules
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            else:
                names = [node.module.split(".")[0]] if node.module else []
            for name in names:
                if name in _BLOCKED_IMPORTS:
                    return f"Import not allowed in sandbox: '{name}'"

        # Block calls to dangerous builtins
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in _BLOCKED_BUILTINS:
                return f"Builtin not allowed in sandbox: '{name}'"

    return None  # code is clean


def _make_preexec_fn(memory_limit_mb: int):
    """Return a preexec_fn that caps memory usage (Unix only)."""
    def _set_limits():
        try:
            import resource
            limit = memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        except (ImportError, ValueError):
            pass  # Windows or unsupported — skip silently
    return _set_limits


class SandboxRunner:
    """Executes Python code in a subprocess with AST-based import blocking and memory limits.

    Security layers:
    1. AST scan — blocks dangerous imports and builtins before execution
    2. Subprocess isolation — code runs in a separate process
    3. Memory cap via resource.setrlimit (Unix only)
    4. Timeout enforced via asyncio.wait_for
    """

    def __init__(
        self,
        timeout: int = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "30")),
        memory_limit_mb: int = 256,
    ):
        self.timeout = timeout
        self.memory_limit_mb = memory_limit_mb

    async def execute_python(
        self,
        code: str,
        input_data: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute Python code in a sandboxed subprocess."""
        # Layer 1: AST check before spawning any process
        ast_error = _check_ast(code)
        if ast_error:
            return {"status": "error", "error": f"Sandbox blocked: {ast_error}"}

        effective_timeout = timeout if timeout is not None else self.timeout

        # Escape single-quoted string for safe embedding in the wrapper script
        escaped_code = code.replace("\\", "\\\\").replace("'", "\\'")

        script = f"""
import json
import pandas as pd
import numpy as np
import statistics
import collections
from datetime import datetime

input_data = {json.dumps(input_data or {})}

def run_user_code():
    try:
        local_scope = {{
            "input_data": input_data,
            "pd": pd, "np": np,
            "statistics": statistics,
            "collections": collections,
            "datetime": datetime,
        }}
        exec('''{escaped_code}''', {{}}, local_scope)
        return {{"status": "success", "result": local_scope.get("result")}}
    except Exception as e:
        return {{"status": "error", "error": f"{{type(e).__name__}}: {{e}}"}}

print(json.dumps(run_user_code()))
"""

        try:
            preexec = _make_preexec_fn(self.memory_limit_mb) if sys.platform != "win32" else None
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-c", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **({"preexec_fn": preexec} if preexec else {}),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=effective_timeout,
            )

            if process.returncode != 0 and stderr:
                return {"status": "error", "error": stderr.decode().strip()}

            output_str = stdout.decode().strip()
            if not output_str:
                return {"status": "error", "error": "No output from sandbox."}

            return json.loads(output_str)

        except asyncio.TimeoutError:
            try:
                process.kill()
            except Exception:
                pass
            return {"status": "error", "error": f"Sandbox timed out after {effective_timeout}s."}
        except Exception as e:
            return {"status": "error", "error": f"Failed to execute sandbox: {e}"}
