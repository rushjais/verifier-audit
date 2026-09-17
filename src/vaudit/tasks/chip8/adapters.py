"""Adapters: drive a third-party interpreter through the `Interpreter` seam.

Each adapter is glue and nothing more — satisfy imports the project only needs for live input,
hand it a headless screen, step it, read its display. The emulation logic stays theirs. Where an
adapter has to repeat setup the project's own front-end performs, that is called out, because a
misconfigured interpreter would look like a wrong one and this study is about not confusing those.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

from .harness import CYCLES_PER_FRAME, Frame
from .manifest import Entry

WIDTH, HEIGHT = 64, 32

_PYGAME_KEYS = ("K_x K_1 K_2 K_3 K_q K_w K_e K_a K_s K_d K_z K_c K_4 K_r K_f K_v").split()


def _stub_pygame() -> None:
    """Satisfy a module-scope `import pygame` used only for live keyboard and sound.

    No input is delivered in this study, so the stub is behaviourally complete: every key reads
    as not-pressed, and sound is discarded. Installing it is glue, not a change to their code.
    """
    if "pygame" in sys.modules:
        return
    pygame = types.ModuleType("pygame")
    key = types.ModuleType("pygame.key")
    key.get_pressed = lambda: {}
    mixer = types.ModuleType("pygame.mixer")
    mixer.init = lambda *a, **k: None
    mixer.quit = lambda *a, **k: None
    mixer.Sound = lambda *a, **k: types.SimpleNamespace(
        play=lambda *a, **k: None, stop=lambda *a, **k: None
    )
    for name in _PYGAME_KEYS:
        setattr(pygame, name, 0)
    pygame.key, pygame.mixer = key, mixer
    sys.modules.update({"pygame": pygame, "pygame.key": key, "pygame.mixer": mixer})


class HeadlessScreen:
    """A 64x32 framebuffer satisfying the screen API these interpreters draw through."""

    def __init__(self) -> None:
        self.pixels = bytearray(WIDTH * HEIGHT)

    def get_width(self) -> int:
        return WIDTH

    def get_height(self) -> int:
        return HEIGHT

    def draw_pixel(self, x: int, y: int, turn_on, bitplane: int = 1) -> None:
        self.pixels[(y % HEIGHT) * WIDTH + (x % WIDTH)] = 1 if turn_on else 0

    def get_pixel(self, x: int, y: int, bitplane: int = 1) -> int:
        return self.pixels[(y % HEIGHT) * WIDTH + (x % WIDTH)]

    def clear_screen(self, bitplane: int = 1) -> None:
        self.pixels = bytearray(WIDTH * HEIGHT)

    def update(self) -> None:
        pass

    def set_extended(self) -> None:
        pass

    def set_normal(self) -> None:
        pass


@dataclass
class craigthomas_adapter:
    """craigthomas/Chip8Python. Chip8CPU(screen) with execute_instruction()."""

    root: Path
    name: str = "craigthomas"
    quirks: dict = field(default_factory=dict)

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        _stub_pygame()
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
        from chip8.cpu import Chip8CPU

        screen = HeadlessScreen()
        cpu = Chip8CPU(screen, **self.quirks)
        # Their emulator.py loads the font as a separate ROM at offset 0; the CPU does not do it
        # itself, and without this every FX29 lookup reads zeroes and nothing is ever drawn.
        cpu.load_rom(str(self.root / "FONTS.chip8"), 0)
        for offset, byte in enumerate(rom):
            cpu.memory[0x200 + offset] = byte

        out: list[Frame] = []
        for _ in range(count):
            for _ in range(CYCLES_PER_FRAME):
                cpu.execute_instruction()
            out.append(bytes(screen.pixels))
        return out


ADAPTERS = {"craigthomas_adapter": craigthomas_adapter}


def build(entry: Entry, root: Path, **kwargs):
    """Instantiate the adapter an entry names."""
    return ADAPTERS[entry.adapter](root=root, name=entry.key, **kwargs)
