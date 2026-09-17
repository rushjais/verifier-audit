"""The population: third-party CHIP-8 interpreters, fetched by pinned commit, never vendored.

WHY NOT VENDORED. Two reasons and both matter. Their licences stay theirs — this repo carries no
one else's code, so it can be published without inheriting anyone's terms. And a pinned commit is
reproducible in a way a copied snapshot is not.

WHY THIRD PARTY. `PREDICTIONS.md`: whoever writes both the population and the metrics can produce
any result they want. A quirk-configurable interpreter of my own sits one import away
(`core.Quirks`), and using its profiles as "the population" would be exactly that failure. Those
profiles are the REFERENCE and a test fixture. The population comes from people who had never
heard of this study.

ADAPTERS ARE GLUE. Each entry needs a shim: satisfy imports it only needs for live input, give it
a headless screen, step it, read its display. The shim is mine and is a few lines; the
interpreter logic behind it stays entirely theirs. Where a shim has to replicate setup the
project's own front-end does (loading a font file, say), that is noted on the entry.
"""

from __future__ import annotations

from dataclasses import dataclass

PERMISSIVE = {"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "ISC", "Unlicense", "CC0-1.0"}


@dataclass(frozen=True)
class Entry:
    """One third-party interpreter. Everything needed to fetch it and to credit it."""

    key: str
    repo: str  # owner/name on GitHub
    commit: str  # pinned; "HEAD" means not yet pinned and not yet usable
    licence: str
    adapter: str  # dotted name of the adapter in `adapters.py`
    notes: str = ""

    @property
    def url(self) -> str:
        return f"https://github.com/{self.repo}.git"

    @property
    def permissive(self) -> bool:
        return self.licence in PERMISSIVE

    @property
    def pinned(self) -> bool:
        return self.commit != "HEAD"

    @property
    def usable(self) -> bool:
        """Only a pinned, permissively licensed entry may enter the population."""
        return self.permissive and self.pinned


# Verified: cloned, driven headlessly, and confirmed to draw the font glyph "0" as 14 lit pixels
# matching the reference. Anything not verified end to end does not belong in this list.
POPULATION: tuple[Entry, ...] = (
    Entry(
        key="craigthomas",
        repo="craigthomas/Chip8Python",
        commit="44d4e7760912a5d91f791cdc8cbdbbee38e07bf8",
        licence="MIT",
        adapter="craigthomas_adapter",
        notes=(
            "Chip8CPU takes a screen object and exposes execute_instruction(). Its quirk flags "
            "(shift/index/jump/clip/logic) are the project's own. Two shim details: pygame is "
            "imported at module scope for live input we never use, and the font is a separate "
            "FONTS.chip8 loaded at offset 0 by their emulator.py rather than by the CPU — the "
            "adapter replicates that setup step. Their font lives at 0x000; mine at 0x050. That "
            "disagreement is itself a finding: a ROM that hardcodes a font address is not "
            "portable, so test ROMs here use FX29."
        ),
    ),
)


def usable_population() -> tuple[Entry, ...]:
    return tuple(e for e in POPULATION if e.usable)


def report() -> str:
    """What the population actually is right now, including what is missing. Printed in the
    writeup verbatim — an overstated n is the easiest way to make this study a lie."""
    lines = [f"population: {len(usable_population())} usable of {len(POPULATION)} listed"]
    for entry in POPULATION:
        blockers = []
        if not entry.permissive:
            blockers.append(f"licence {entry.licence}")
        if not entry.pinned:
            blockers.append("commit not pinned")
        status = "usable" if entry.usable else "BLOCKED: " + ", ".join(blockers)
        lines.append(f"  {entry.key:<16} {entry.repo:<34} {entry.licence:<12} {status}")
    return "\n".join(lines)
