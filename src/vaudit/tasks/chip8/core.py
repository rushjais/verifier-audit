"""A CHIP-8 interpreter, quirk-configurable, fully deterministic.

Its job in this study is to be the reference — the Mesen2 analogue — and to make the harness
testable offline. It is MINE, and that is stated wherever its numbers appear: the population of
correct implementations must come from elsewhere, or the study measures nothing (PREDICTIONS.md).

Determinism matters more here than anywhere else in the repo. `CXNN` is the only source of
randomness in CHIP-8 and it is driven by a seeded PRNG, so the same ROM and seed always produce
the same frames. A grading study whose reference drifts between runs cannot measure anything.

THE QUIRKS. Independently written interpreters genuinely disagree on five behaviours, and both
sides of each are defensible — the original COSMAC VIP did one thing, the later CHIP-48 and
SUPER-CHIP interpreters another, and ROMs exist that depend on each. That disagreement is the
honest variation this study needs, which is why they are configuration and not constants.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

WIDTH, HEIGHT = 64, 32
PROGRAM_START = 0x200
FONT_START = 0x50

# Standard 4x5 hex font, 0-F.
FONT = bytes(
    [
        0xF0,
        0x90,
        0x90,
        0x90,
        0xF0,
        0x20,
        0x60,
        0x20,
        0x20,
        0x70,
        0xF0,
        0x10,
        0xF0,
        0x80,
        0xF0,
        0xF0,
        0x10,
        0xF0,
        0x10,
        0xF0,
        0x90,
        0x90,
        0xF0,
        0x10,
        0x10,
        0xF0,
        0x80,
        0xF0,
        0x10,
        0xF0,
        0xF0,
        0x80,
        0xF0,
        0x90,
        0xF0,
        0xF0,
        0x10,
        0x20,
        0x40,
        0x40,
        0xF0,
        0x90,
        0xF0,
        0x90,
        0xF0,
        0xF0,
        0x90,
        0xF0,
        0x10,
        0xF0,
        0xF0,
        0x90,
        0xF0,
        0x90,
        0x90,
        0xE0,
        0x90,
        0xE0,
        0x90,
        0xE0,
        0xF0,
        0x80,
        0x80,
        0x80,
        0xF0,
        0xE0,
        0x90,
        0x90,
        0x90,
        0xE0,
        0xF0,
        0x80,
        0xF0,
        0x80,
        0xF0,
        0xF0,
        0x80,
        0xF0,
        0x80,
        0x80,
    ]
)


@dataclass(frozen=True)
class Quirks:
    """The five documented disagreements. Defaults follow the original COSMAC VIP."""

    shift_uses_vy: bool = True  # 8XY6/8XYE shift VY into VX, vs shifting VX in place
    memory_increments_i: bool = True  # FX55/FX65 leave I advanced, vs leaving it untouched
    jump_uses_vx: bool = False  # BNNN adds V0, vs adding VX (the CHIP-48 reading)
    vf_reset: bool = True  # 8XY1/2/3 clear VF as a side effect
    sprites_wrap: bool = False  # sprites wrap around the edge, vs clipping at it

    @property
    def label(self) -> str:
        return ",".join(name for name, value in sorted(self.__dict__.items()) if value) or "none"


COSMAC_VIP = Quirks()
CHIP48 = Quirks(shift_uses_vy=False, memory_increments_i=False, jump_uses_vx=True, vf_reset=False)


@dataclass
class Chip8:
    """One interpreter instance. `display` is the framebuffer the study compares."""

    quirks: Quirks = COSMAC_VIP
    seed: int = 0
    memory: bytearray = field(default_factory=lambda: bytearray(4096))
    v: bytearray = field(default_factory=lambda: bytearray(16))
    display: bytearray = field(default_factory=lambda: bytearray(WIDTH * HEIGHT))
    stack: list[int] = field(default_factory=list)
    i: int = 0
    pc: int = PROGRAM_START
    delay: int = 0
    sound: int = 0
    keys: int = 0  # bitmask; no input in this study, so it stays 0
    halted: bool = False

    def __post_init__(self):
        self.memory[FONT_START : FONT_START + len(FONT)] = FONT
        self._rng = random.Random(self.seed)

    def load(self, rom: bytes) -> Chip8:
        if PROGRAM_START + len(rom) > len(self.memory):
            raise ValueError(f"ROM too large: {len(rom)} bytes")
        self.memory[PROGRAM_START : PROGRAM_START + len(rom)] = rom
        return self

    # -- helpers ------------------------------------------------------------------------
    def _pixel(self, x: int, y: int) -> int:
        return self.display[y * WIDTH + x]

    def _draw(self, vx: int, vy: int, height: int) -> None:
        """Draw a sprite; VF records whether any lit pixel was turned off."""
        x0, y0 = self.v[vx] % WIDTH, self.v[vy] % HEIGHT
        self.v[0xF] = 0
        for row in range(height):
            y = y0 + row
            if self.quirks.sprites_wrap:
                y %= HEIGHT
            elif y >= HEIGHT:
                break
            byte = self.memory[(self.i + row) & 0xFFF]
            for bit in range(8):
                if not (byte >> (7 - bit)) & 1:
                    continue
                x = x0 + bit
                if self.quirks.sprites_wrap:
                    x %= WIDTH
                elif x >= WIDTH:
                    break
                index = y * WIDTH + x
                if self.display[index]:
                    self.v[0xF] = 1
                self.display[index] ^= 1

    # -- the loop -----------------------------------------------------------------------
    def step(self) -> None:
        """Execute one instruction. An unknown opcode halts rather than guessing."""
        if self.halted or self.pc + 1 >= len(self.memory):
            self.halted = True
            return
        op = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc = (self.pc + 2) & 0xFFF
        x, y = (op >> 8) & 0xF, (op >> 4) & 0xF
        n, nn, nnn = op & 0xF, op & 0xFF, op & 0xFFF
        q = self.quirks

        match op >> 12:
            case 0x0 if op == 0x00E0:
                self.display = bytearray(WIDTH * HEIGHT)
            case 0x0 if op == 0x00EE:
                self.pc = self.stack.pop() if self.stack else self._halt()
            case 0x1:
                if nnn == self.pc - 2:
                    self.halted = True  # tight self-loop: the ROM is done
                self.pc = nnn
            case 0x2:
                self.stack.append(self.pc)
                self.pc = nnn
            case 0x3:
                self.pc += 2 if self.v[x] == nn else 0
            case 0x4:
                self.pc += 2 if self.v[x] != nn else 0
            case 0x5 if n == 0:
                self.pc += 2 if self.v[x] == self.v[y] else 0
            case 0x6:
                self.v[x] = nn
            case 0x7:
                self.v[x] = (self.v[x] + nn) & 0xFF
            case 0x8:
                self._arithmetic(x, y, n)
            case 0x9 if n == 0:
                self.pc += 2 if self.v[x] != self.v[y] else 0
            case 0xA:
                self.i = nnn
            case 0xB:
                self.pc = (nnn + self.v[x if q.jump_uses_vx else 0]) & 0xFFF
            case 0xC:
                self.v[x] = self._rng.randrange(256) & nn
            case 0xD:
                self._draw(x, y, n)
            case 0xE if nn == 0x9E:
                self.pc += 2 if (self.keys >> (self.v[x] & 0xF)) & 1 else 0
            case 0xE if nn == 0xA1:
                self.pc += 2 if not (self.keys >> (self.v[x] & 0xF)) & 1 else 0
            case 0xF:
                self._misc(x, nn)
            case _:
                self.halted = True

    def _halt(self) -> int:
        self.halted = True
        return self.pc

    def _arithmetic(self, x: int, y: int, n: int) -> None:
        q = self.quirks
        match n:
            case 0x0:
                self.v[x] = self.v[y]
            case 0x1 | 0x2 | 0x3:
                op = {0x1: int.__or__, 0x2: int.__and__, 0x3: int.__xor__}[n]
                self.v[x] = op(self.v[x], self.v[y])
                if q.vf_reset:
                    self.v[0xF] = 0
            case 0x4:
                total = self.v[x] + self.v[y]
                self.v[x] = total & 0xFF
                self.v[0xF] = int(total > 0xFF)
            case 0x5:
                borrow = int(self.v[x] >= self.v[y])
                self.v[x] = (self.v[x] - self.v[y]) & 0xFF
                self.v[0xF] = borrow
            case 0x6:
                source = self.v[y] if q.shift_uses_vy else self.v[x]
                self.v[x] = (source >> 1) & 0xFF
                self.v[0xF] = source & 1
            case 0x7:
                borrow = int(self.v[y] >= self.v[x])
                self.v[x] = (self.v[y] - self.v[x]) & 0xFF
                self.v[0xF] = borrow
            case 0xE:
                source = self.v[y] if q.shift_uses_vy else self.v[x]
                self.v[x] = (source << 1) & 0xFF
                self.v[0xF] = (source >> 7) & 1
            case _:
                self.halted = True

    def _misc(self, x: int, nn: int) -> None:
        match nn:
            case 0x07:
                self.v[x] = self.delay
            case 0x0A:
                self.pc -= 2  # block on input; with no keys this halts progress
                self.halted = True
            case 0x15:
                self.delay = self.v[x]
            case 0x18:
                self.sound = self.v[x]
            case 0x1E:
                self.i = (self.i + self.v[x]) & 0xFFF
            case 0x29:
                self.i = FONT_START + (self.v[x] & 0xF) * 5
            case 0x33:
                value = self.v[x]
                self.memory[self.i] = value // 100
                self.memory[(self.i + 1) & 0xFFF] = (value // 10) % 10
                self.memory[(self.i + 2) & 0xFFF] = value % 10
            case 0x55 | 0x65:
                for offset in range(x + 1):
                    address = (self.i + offset) & 0xFFF
                    if nn == 0x55:
                        self.memory[address] = self.v[offset]
                    else:
                        self.v[offset] = self.memory[address]
                if self.quirks.memory_increments_i:
                    self.i = (self.i + x + 1) & 0xFFF
            case _:
                self.halted = True

    def tick_timers(self) -> None:
        self.delay = max(0, self.delay - 1)
        self.sound = max(0, self.sound - 1)
