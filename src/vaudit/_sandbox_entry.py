"""Child-process entry point: apply limits, then run one script in a working directory.

Runs as `python -m vaudit._sandbox_entry <work_dir> <script> <mem_mb> <cpu_seconds>`.

The limits here are a containment boundary, not a security boundary. They stop a runaway or
careless candidate from taking the host down; they are not a defence against a determined
attacker with local code execution. Untrusted code at scale belongs in a container.
"""

import os
import resource
import runpy
import socket
import sys


def _blocked(*_args, **_kwargs):
    raise OSError("network access is disabled in the sandbox")


def _limit(which: int, value: int) -> None:
    """Lower a resource limit, clamped to the existing hard limit, tolerating refusal.

    Platforms differ about what they will accept: macOS rejects an RLIMIT_AS soft limit above
    its hard limit with ValueError, and a raise here would kill the child BEFORE it runs the
    candidate. That failure mode is worse than no limit at all — every run would look like a
    crash, every exploit would look sealed, and every measurement would read zero for a reason
    unrelated to the code under test. The parent's wall-clock timeout is the guarantee that
    holds everywhere; these limits are best-effort containment on top of it.
    """
    try:
        _soft, hard = resource.getrlimit(which)
    except (ValueError, OSError):
        return
    if hard != resource.RLIM_INFINITY:
        value = min(value, hard)
    try:
        resource.setrlimit(which, (value, hard))
    except (ValueError, OSError):
        pass


def main() -> int:
    work_dir, script, mem_mb, cpu_seconds = sys.argv[1:5]

    _limit(resource.RLIMIT_AS, int(mem_mb) * 1024 * 1024)
    _limit(resource.RLIMIT_CPU, int(cpu_seconds))
    _limit(resource.RLIMIT_NPROC, 64)  # no fork bombs

    # Nothing here needs the network, so anything reaching for it is either a mistake or a
    # side channel. Blocking at the socket constructor covers both.
    socket.socket = _blocked
    socket.create_connection = _blocked

    os.chdir(work_dir)
    sys.path.insert(0, work_dir)
    runpy.run_path(os.path.join(work_dir, script), run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main())
