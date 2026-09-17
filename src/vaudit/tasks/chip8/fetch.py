"""Fetch the population at its pinned commits. Nothing here is committed to this repo.

python -m vaudit.tasks.chip8.fetch          # clone/checkout every usable entry
python -m vaudit.tasks.chip8.fetch --status # what is on disk right now
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from .manifest import POPULATION, Entry, report

POPULATION_DIR = Path(".population")


def path_for(entry: Entry) -> Path:
    return POPULATION_DIR / entry.key


def is_fetched(entry: Entry) -> bool:
    """On disk AND at the pinned commit — a drifted checkout is not the thing we measured."""
    path = path_for(entry)
    if not (path / ".git").exists():
        return False
    head = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return head.returncode == 0 and head.stdout.strip() == entry.commit


def fetch(entry: Entry) -> bool:
    if not entry.usable:
        print(f"skip {entry.key}: not usable ({entry.licence}, pinned={entry.pinned})")
        return False
    if is_fetched(entry):
        print(f"ok   {entry.key}: already at {entry.commit[:8]}")
        return True
    path = path_for(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not (path / ".git").exists():
        subprocess.run(["git", "clone", "-q", entry.url, str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "checkout", "-q", entry.commit], check=True)
    print(f"got  {entry.key}: {entry.repo} @ {entry.commit[:8]} ({entry.licence})")
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="fetch the CHIP-8 population")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)

    print(report())
    if args.status:
        print()
        for entry in POPULATION:
            print(f"  {entry.key:<16} {'fetched' if is_fetched(entry) else 'not fetched'}")
        return 0

    print()
    for entry in POPULATION:
        fetch(entry)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
