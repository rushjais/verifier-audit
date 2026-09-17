"""Run a ROM to a deterministic sequence of framebuffers, whoever wrote the interpreter.

This is the comparable surface the grading strategies score. Everything in the study reduces to:
run the reference and a candidate over the same ROM, get two equal-length frame sequences, and
ask a metric how close they are.

`Interpreter` is the seam a third-party implementation is adapted to. Adapters are glue — import
someone's interpreter, step it, read its display — and are labelled as glue. The interpreter
logic behind each one stays theirs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .core import HEIGHT, WIDTH, Chip8, Quirks

# One frame: WIDTH*HEIGHT bytes, each 0 or 1. Bytes rather than a nested list so frames hash,
# compare, and serialise cheaply — there will be thousands of them.
Frame = bytes

CYCLES_PER_FRAME = 15  # ~900 instructions/second at 60fps, the conventional CHIP-8 rate
BLANK: Frame = bytes(WIDTH * HEIGHT)


@runtime_checkable
class Interpreter(Protocol):
    name: str

    def frames(self, rom: bytes, count: int) -> list[Frame]: ...


@dataclass
class NativeInterpreter:
    """The reference implementation, and the quirk-variant harness. Mine, not the population."""

    name: str
    quirks: Quirks
    seed: int = 0
    cycles_per_frame: int = CYCLES_PER_FRAME

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        """Exactly `count` frames. A halted ROM repeats its last frame rather than ending early,
        so every sequence is the same length and metrics compare like with like."""
        machine = Chip8(quirks=self.quirks, seed=self.seed).load(rom)
        out: list[Frame] = []
        for _ in range(count):
            for _ in range(self.cycles_per_frame):
                if machine.halted:
                    break
                machine.step()
            machine.tick_timers()
            out.append(bytes(machine.display))
        return out


def render(frame: Frame) -> str:
    """A frame as text. For eyeballing a disagreement before trusting a number about it."""
    rows = []
    for y in range(HEIGHT):
        row = frame[y * WIDTH : (y + 1) * WIDTH]
        rows.append("".join("#" if pixel else "." for pixel in row))
    return "\n".join(rows)


def lit(frame: Frame) -> int:
    return sum(frame)
