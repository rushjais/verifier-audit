"""Adapters: drive a third-party interpreter through the `Interpreter` seam.

Each adapter is glue and nothing more — satisfy imports the project only needs for live input,
hand it a headless screen, step it, read its display. The emulation logic stays theirs. Where an
adapter has to repeat setup the project's own front-end performs, that is called out, because a
misconfigured interpreter would look like a wrong one and this study is about not confusing those.
"""

from __future__ import annotations

import sys
import tempfile
import types
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from .harness import CYCLES_PER_FRAME, Frame
from .manifest import Entry

WIDTH, HEIGHT = 64, 32

_PYGAME_KEYS = ("K_x K_1 K_2 K_3 K_q K_w K_e K_a K_s K_d K_z K_c K_4 K_r K_f K_v").split()


def _stub_pygame() -> None:
    """Satisfy a module-scope `import pygame` used only for live keyboard, sound, and a window.

    No input is delivered in this study and nothing is displayed, so the stub is behaviourally
    complete: every key reads as not-pressed, sound is discarded, and the window is a stand-in.
    Installing it is glue, not a change to their code — every pixel decision still happens in
    their own screen class, which is why these adapters use theirs rather than substituting mine.
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
    surface = types.SimpleNamespace(
        fill=lambda *a, **k: None, blit=lambda *a, **k: None, get_size=lambda: (64, 32)
    )
    display = types.ModuleType("pygame.display")
    display.set_mode = lambda *a, **k: surface
    display.set_caption = lambda *a, **k: None
    display.update = lambda *a, **k: None
    display.flip = lambda *a, **k: None
    event = types.ModuleType("pygame.event")
    event.get = lambda *a, **k: []
    event.pump = lambda *a, **k: None
    draw = types.ModuleType("pygame.draw")
    draw.rect = lambda *a, **k: None
    for name in _PYGAME_KEYS:
        setattr(pygame, name, 0)
    pygame.Rect = lambda *a, **k: types.SimpleNamespace()
    pygame.QUIT = 256
    pygame.init = lambda *a, **k: None
    pygame.quit = lambda *a, **k: None
    pygame.key, pygame.mixer, pygame.display = key, mixer, display
    pygame.event, pygame.draw = event, draw
    sys.modules.update(
        {
            "pygame": pygame,
            "pygame.key": key,
            "pygame.mixer": mixer,
            "pygame.display": display,
            "pygame.event": event,
            "pygame.draw": draw,
        }
    )


@contextmanager
def _isolated(root: Path, *top_level: str):
    """Import from `root` with the named top-level modules purged before and after.

    Several of these projects ship a package called `chip8`. Without this, importing one and then
    another silently hands the second the first one's code — and two implementations that are
    literally the same code look perfectly in agreement. That is the most dangerous possible
    false result for this study, so the isolation is not optional and is tested.
    """

    def purge():
        for name in list(sys.modules):
            if name in top_level or any(name.startswith(f"{t}.") for t in top_level):
                del sys.modules[name]

    saved_path = list(sys.path)
    purge()
    sys.path.insert(0, str(root))
    try:
        yield
    finally:
        purge()
        sys.path[:] = saved_path


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
        with _isolated(self.root, "chip8"):
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


@dataclass
class wyattferguson_adapter:
    """wyattferguson/chip8-emulator. CPU(ram, screen, keypad, audio) with cycle().

    Uses THEIR Screen, not a stand-in: `flip_pixel` contains their wrap decision, so swapping in
    my own framebuffer would quietly replace their behaviour with mine. RAM loads from a path, so
    the ROM is written to a temp file.
    """

    root: Path
    name: str = "wyattferguson"
    quirks: dict = field(default_factory=dict)

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        _stub_pygame()
        with _isolated(self.root, "chip8"):
            from chip8.audio import Audio
            from chip8.cpu import CPU
            from chip8.keypad import Keypad
            from chip8.ram import RAM
            from chip8.screen import Screen

        with tempfile.TemporaryDirectory() as tmp:
            rom_path = Path(tmp) / "rom.ch8"
            rom_path.write_bytes(rom)
            cpu = CPU(RAM(str(rom_path)), Screen(), Keypad(), Audio(mute=True))
            out: list[Frame] = []
            for _ in range(count):
                cpu.cycle()  # their cycle() is already one tick's worth of instructions
                out.append(_from_rows(cpu.screen.buffer))
            return out


class DebugloopUI:
    """The UI seam debugloop/chip8 draws through, mirrored exactly.

    Theirs stores lit pixels as an unbounded set of (x, y) and neither wraps nor clips while
    drawing; only `screen_redraw` bounds what is shown. So this keeps the set unbounded and
    bounds at frame-capture time. Mirroring that matters: their collision detection reads the
    same unbounded set, so imposing wrapping here would change behaviour they did not write.
    """

    def __init__(self) -> None:
        self.screen_contents: set[tuple[int, int]] = set()

    def clear_screen(self) -> None:
        self.screen_contents = set()

    def toggle_pixel(self, x: int, y: int) -> None:
        self.screen_contents ^= {(x, y)}

    def get_pixel(self, x: int, y: int) -> bool:
        return (x, y) in self.screen_contents

    def get_key(self, _k) -> bool:
        return False

    def wait_key(self) -> int:
        return 0

    def update_code_window(self, *_a, **_k) -> None:
        pass

    def update_var_window(self, *_a, **_k) -> None:
        pass

    def screen_redraw(self, *_a, **_k) -> None:
        """Their cycle() repaints every fifth tick. Nothing to repaint here; the set IS the
        display, and frames are captured from it directly."""
        pass

    def frame(self) -> Frame:
        pixels = bytearray(WIDTH * HEIGHT)
        for x, y in self.screen_contents:
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                pixels[y * WIDTH + x] = 1
        return bytes(pixels)


@dataclass
class debugloop_adapter:
    """debugloop/chip8. Chip8(filename, ui) with cycle(). No pygame; curses lives in ui.py,
    which is never imported."""

    root: Path
    name: str = "debugloop"
    quirks: dict = field(default_factory=dict)

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        with _isolated(self.root, "emu", "ui"):
            import emu

            # Their cycle() sleeps 1/300s to pace a live game and calls screen_redraw every
            # fifth cycle. Neither affects a single pixel; both are removed so a study with
            # thousands of frames finishes. Nothing that decides output is touched.
            emu.time = types.SimpleNamespace(sleep=lambda _s: None)

        with tempfile.TemporaryDirectory() as tmp:
            rom_path = Path(tmp) / "rom.ch8"
            rom_path.write_bytes(rom)
            ui = DebugloopUI()
            machine = emu.Chip8(str(rom_path), ui)
            out: list[Frame] = []
            for _ in range(count):
                for _ in range(CYCLES_PER_FRAME):
                    machine.cycle()
                out.append(ui.frame())
            return out


def _from_rows(rows) -> Frame:
    """Flatten a row-major 2D buffer into the flat frame the metrics compare."""
    pixels = bytearray(WIDTH * HEIGHT)
    for y, row in enumerate(rows[:HEIGHT]):
        for x, pixel in enumerate(row[:WIDTH]):
            pixels[y * WIDTH + x] = 1 if pixel else 0
    return bytes(pixels)


ADAPTERS = {
    "craigthomas_adapter": craigthomas_adapter,
    "debugloop_adapter": debugloop_adapter,
    "wyattferguson_adapter": wyattferguson_adapter,
}


def build(entry: Entry, root: Path, **kwargs):
    """Instantiate the adapter an entry names."""
    return ADAPTERS[entry.adapter](root=root, name=entry.key, **kwargs)
