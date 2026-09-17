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

# THE FRAME RULE. One frame is exactly this many instructions, executed by every interpreter,
# whoever wrote it. It is enforced per adapter and tested, because it is not free: these projects
# disagree about it (wyattferguson runs 12 per tick, debugloop 1 per cycle), and comparing a frame
# built from 12 instructions against one built from 15 measures pacing, not correctness.
#
# What is deliberately NOT normalised is timer semantics. craigthomas decrements on demand,
# wyattferguson once per cycle(), and debugloop every fifth cycle via a counter it never resets —
# so after the fifth it decrements on every one. Making those agree would mean rewriting their
# code, which is the line this study does not cross. It is a documented limitation: any ROM whose
# final frame depends on delay-timer pacing is not safely comparable across this population.
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
    instructions: int = 0

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        """Exactly `count` frames. A halted ROM repeats its last frame rather than ending early,
        so every sequence is the same length and metrics compare like with like."""
        machine = Chip8(quirks=self.quirks, seed=self.seed).load(rom)
        self.instructions = 0
        out: list[Frame] = []
        for _ in range(count):
            for _ in range(self.cycles_per_frame):
                if machine.halted:
                    break
                machine.step()
                self.instructions += 1
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
