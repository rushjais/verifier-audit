"""Test ROMs. Fetched at a pinned commit, never committed here, never redistributed.

SOURCE AND LICENCE. Timendus/chip8-test-suite, GPL-3.0. This repository carries none of it: the
fetch script clones it at a pinned commit into a gitignored directory, and nothing from it is
redistributed. Running a GPL'd program as test input and reporting what happened does not make
the measuring code derivative of it. Credit belongs in the writeup, prominently — this suite is
the reason the study has anything to disagree about.

THE ROMS DO TWO JOBS, and keeping them straight is the difference between a finding and a bug:

  CORRECTNESS (corax+, flags) decides who is even eligible for the population. An interpreter
  that fails these is not "correct but different" — it is wrong, and including it would turn a
  bug of theirs into a fairness finding of mine. That is the single easiest way to fake this
  study's headline, so the gate runs first.

  DISAGREEMENT (quirks) is what the grading strategies then have to rank. It exercises the five
  behaviours independently written interpreters genuinely differ on, which is precisely what a
  differential grader against one reference has to cope with.

  QUIRK-FREE (ibm-logo, chip8-logo) is the control: every correct interpreter should agree here,
  so a disagreement on these means an adapter is broken, not that an implementation is.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUITE_REPO = "Timendus/chip8-test-suite"
SUITE_COMMIT = "742e9eac9f5d44466c1c9d83fcaa8158c6683cb1"
SUITE_LICENCE = "GPL-3.0"
SUITE_URL = f"https://github.com/{SUITE_REPO}.git"
ROM_DIR = Path(".population/roms")


@dataclass(frozen=True)
class Rom:
    key: str
    filename: str
    role: str  # "quirk-free" | "correctness" | "disagreement"
    purpose: str
    usable: bool = True
    timer_dependent: bool = False  # Amendment 2 rule 3: excluded from the study
    self_verifying: bool = False  # renders its own pass/fail marks
    needs_input: bool = False  # requires live key presses this harness never delivers

    @property
    def path(self) -> Path:
        return ROM_DIR / "bin" / self.filename

    def load(self) -> bytes:
        return self.path.read_bytes()

    @property
    def available(self) -> bool:
        return self.path.exists()


ROMS: tuple[Rom, ...] = (
    Rom(
        "chip8_logo",
        "1-chip8-logo.ch8",
        "quirk-free",
        "draws a logo using only uncontroversial opcodes; every correct interpreter agrees",
    ),
    Rom(
        "ibm_logo",
        "2-ibm-logo.ch8",
        "quirk-free",
        "the canonical first-ROM-that-works; agreement here is the adapter sanity check",
    ),
    Rom(
        "corax",
        "3-corax+.ch8",
        "correctness",
        "per-opcode correctness; failing it means wrong, not different",
        self_verifying=True,
    ),
    Rom(
        "flags",
        "4-flags.ch8",
        "correctness",
        "VF/flag correctness across arithmetic and logical ops",
        self_verifying=True,
    ),
    Rom(
        "quirks",
        "5-quirks.ch8",
        "disagreement",
        "exercises the five behaviours correct interpreters genuinely disagree on — but its "
        "delay-timer loop MEASURES interpreter speed to test the display-wait quirk, and timer "
        "semantics are not normalised across this population, so Amendment 2 rule 3 excludes it",
        usable=False,
        timer_dependent=True,
    ),
    Rom(
        "keypad",
        "6-keypad.ch8",
        "disagreement",
        "requires live key input, which this harness never delivers",
        usable=False,
        timer_dependent=True,
        self_verifying=True,
        needs_input=True,
    ),
)


BY_KEY = {rom.key: rom for rom in ROMS}


def usable_roms() -> tuple[Rom, ...]:
    return tuple(r for r in ROMS if r.usable)


def by_role(role: str) -> tuple[Rom, ...]:
    return tuple(r for r in usable_roms() if r.role == role)


def report() -> str:
    lines = [f"roms: {SUITE_REPO} @ {SUITE_COMMIT[:8]} ({SUITE_LICENCE}, fetched, not vendored)"]
    for rom in ROMS:
        state = "present" if rom.available else "not fetched"
        reasons = []
        if rom.needs_input:
            reasons.append("needs live input")
        if rom.timer_dependent:
            reasons.append("timer-dependent")
        note = "" if rom.usable else "  EXCLUDED: " + ", ".join(reasons or ["unusable"])
        lines.append(f"  {rom.key:<12} {rom.role:<13} {state:<12}{note}")
    return "\n".join(lines)
