"""Cheat submissions: the catch-rate population. MINE, and labelled as mine everywhere.

Each one is a plausible way to score well without emulating anything — the CHIP-8 analogue of
GBA Eval's "an emulator that just renders a white screen". They exist to answer the other half
of every grading strategy: a metric that accepts every correct interpreter is worthless if it
also accepts these.

They are derived from the reference's own frames, which is the point: a cheat that had to
compute the right answer to look close would not be a cheat.
"""

from __future__ import annotations

from dataclasses import dataclass

from .harness import BLANK, Frame, Interpreter


@dataclass
class BlankScreen:
    """Renders nothing at all. On a mostly-off display this scores well under pixel counting."""

    name: str = "cheat:blank_screen"

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        return [BLANK] * count


@dataclass
class FrozenFirstFrame:
    """Runs the reference for exactly one frame, then stops and repeats it forever."""

    reference: Interpreter
    name: str = "cheat:frozen_first_frame"

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        first = self.reference.frames(rom, 1)[0]
        return [first] * count


@dataclass
class InvertedPalette:
    """Pixel-perfect, every pixel wrong. Identical structure, inverted values."""

    reference: Interpreter
    name: str = "cheat:inverted_palette"

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        return [bytes(1 - pixel for pixel in frame) for frame in self.reference.frames(rom, count)]


@dataclass
class OneFrameLate:
    """Correct, one frame behind. Not really a cheat — a timing difference a human would not
    notice — and it is here to catch strategies that punish it as if it were one."""

    reference: Interpreter
    name: str = "cheat:one_frame_late"

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        frames = self.reference.frames(rom, count)
        return [frames[0], *frames[:-1]]


def all_cheats(reference: Interpreter) -> list[Interpreter]:
    return [
        BlankScreen(),
        FrozenFirstFrame(reference),
        InvertedPalette(reference),
        OneFrameLate(reference),
    ]
