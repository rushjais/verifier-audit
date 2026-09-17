"""Run one script in a child process under hard limits.

Deliberately thinner than a test-runner sandbox. Callers here do not need pass/fail semantics
from a test framework — they need "run this, enforce the limits, tell me whether it finished."
The actual verdict always comes from what the script WROTE, checked by the parent
(`isolation.score_isolated`), never from an exit status. That matters: a candidate can call
`os._exit(0)` during import and fake a clean exit, but it cannot fabricate output values it
never computed.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

DEFAULT_TIMEOUT = 30.0
DEFAULT_MEM_MB = 2048
_ENTRY = "vaudit._sandbox_entry"


def _child_env() -> dict:
    """A deterministic environment: no inherited import paths, no proxies, fixed hash seed."""
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONSTARTUP", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        env.pop(key, None)
        env.pop(key.lower(), None)
    env["PYTHONHASHSEED"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_script(
    work_dir: str | Path,
    script: str,
    timeout: float = DEFAULT_TIMEOUT,
    mem_mb: int = DEFAULT_MEM_MB,
) -> bool:
    """Run `script` inside `work_dir`. True iff it finished on its own within the limits.

    A timeout kills the whole process group — a child that spawned helpers should not outlive it.
    True here means "it ran", never "it passed"; the caller decides that from the output.
    """
    cmd = [
        sys.executable,
        "-s",
        "-m",
        _ENTRY,
        str(work_dir),
        script,
        str(mem_mb),
        str(int(timeout) + 1),
    ]
    proc = subprocess.Popen(
        cmd,
        env=_child_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        proc.communicate()
        return False
    return proc.returncode == 0
