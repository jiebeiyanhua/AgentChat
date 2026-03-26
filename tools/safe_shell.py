import re
import subprocess
from pathlib import Path

from langchain_core.tools import tool

WORKDIR = Path.cwd()
MAX_OUTPUT_CHARS = 4000
ALLOWED_COMMAND_PREFIXES = {
    "dir",
    "ls",
    "pwd",
    "cd",
    "echo",
    "type",
    "cat",
    "rg",
    "where",
    "whoami",
    "git status",
    "git diff",
    "git branch",
    "python --version",
    "pip list",
}
BLOCKED_PATTERNS = [
    r"\brm\b",
    r"\bdel\b",
    r"\berase\b",
    r"\bmove-item\b",
    r"\bremove-item\b",
    r"\bren\b",
    r"\brename-item\b",
    r"\bcopy-item\b",
    r"\bset-content\b",
    r"\badd-content\b",
    r"\bout-file\b",
    r">",
    r"\bformat\b",
    r"\bshutdown\b",
    r"\brestart\b",
    r"\bsc\b",
    r"\breg\b",
    r"\btaskkill\b",
    r"\bnet user\b",
    r"\bmkfs\b",
    r"\bchmod\b",
    r"\bchown\b",
]


def is_command_allowed(command: str) -> bool:
    normalized = " ".join(command.strip().lower().split())
    if not normalized:
        return False

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, normalized):
            return False

    return any(normalized.startswith(prefix) for prefix in ALLOWED_COMMAND_PREFIXES)


@tool
def safe_shell(command: str) -> str:
    """Run a read-only shell command for inspection only. Destructive or file-modifying commands are blocked."""
    if not is_command_allowed(command):
        return (
            "Command blocked. Only read-only inspection commands are allowed, "
            "for example: dir, ls, pwd, type, cat, rg, git status, git diff."
        )

    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            cwd=str(WORKDIR),
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return "Command timed out after 15 seconds."
    except Exception as exc:
        return f"Command failed: {exc}"

    output = (completed.stdout or completed.stderr or "").strip()
    if not output:
        output = "Command completed with no output."

    if len(output) > MAX_OUTPUT_CHARS:
        output = f"{output[:MAX_OUTPUT_CHARS]}..."

    status = "success" if completed.returncode == 0 else f"exit_code={completed.returncode}"
    return f"[{status}] {output}"
