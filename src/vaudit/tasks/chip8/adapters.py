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


class _NoKeysPressed:
    """What pygame.key.get_pressed() returns when nothing is held: indexable, always False."""

    def __getitem__(self, _index) -> bool:
        return False

    def __len__(self) -> int:
        return 512  # larger than any pygame key constant


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
    # pygame.key.get_pressed() returns a SEQUENCE indexable by any key constant. Returning {}
    # raised KeyError the moment an interpreter executed EX9E (skip-if-key-pressed), which read
    # as "this interpreter crashes on the quirks ROM" and nearly got a working implementation
    # excluded from the population as broken. Model the real contract: indexable by anything,
    # always not-pressed.
    key.get_pressed = lambda: _NoKeysPressed()
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
    # Distinct values: their code maps CHIP-8 keys onto these constants, and making them all
    # equal would silently collapse sixteen keys into one.
    for index, name in enumerate(_PYGAME_KEYS):
        setattr(pygame, name, index + 1)
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
    instructions: int = 0  # instructions actually executed by the last frames() call

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

        self.instructions = 0
        out: list[Frame] = []
        for _ in range(count):
            for _ in range(CYCLES_PER_FRAME):
                cpu.execute_instruction()
                self.instructions += 1
            cpu.decrement_timers()  # their emulator.py does this per frame; the CPU does not
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
    instructions: int = 0  # instructions actually executed by the last frames() call

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        _stub_pygame()
        with _isolated(self.root, "chip8"):
            import chip8.cpu as cpu_module
            from chip8.audio import Audio
            from chip8.cpu import CPU
            from chip8.keypad import Keypad
            from chip8.ram import RAM
            from chip8.screen import Screen

            # Their cycle() is one 60Hz tick: timers once, then CPU_CYCLES_PER_TICK instructions.
            # That constant is 12; the study's frame is CYCLES_PER_FRAME. Retuning it is a
            # configuration change of the same kind as setting a quirk flag — no logic is
            # altered — and without it this adapter would build frames from 12 instructions
            # while every other built them from 15.
            cpu_module.CPU_CYCLES_PER_TICK = CYCLES_PER_FRAME

        with tempfile.TemporaryDirectory() as tmp:
            rom_path = Path(tmp) / "rom.ch8"
            rom_path.write_bytes(rom)
            cpu = CPU(RAM(str(rom_path)), Screen(), Keypad(), Audio(mute=True))
            self.instructions = 0
            decode = cpu.decode

            def counted_decode():
                self.instructions += 1
                return decode()

            cpu.decode = counted_decode

            out: list[Frame] = []
            for _ in range(count):
                cpu.cycle()  # one tick: timers once, then CYCLES_PER_FRAME instructions
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
    instructions: int = 0  # instructions actually executed by the last frames() call

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
            self.instructions = 0
            out: list[Frame] = []
            for _ in range(count):
                for _ in range(CYCLES_PER_FRAME):
                    machine.cycle()  # their cycle() is exactly one instruction
                    self.instructions += 1
                out.append(ui.frame())
            return out


@dataclass
class islay_adapter:
    """IslayLaphroaig/CHIP-8. Chip8() with cycle() = one instruction and a flat display list.

    No GUI dependency of any kind. Their main.py loads the font from a `font_set` file at offset
    0 before the ROM at 512; the adapter does the same, since the CPU does not do it itself.
    """

    root: Path
    name: str = "islay"
    quirks: dict = field(default_factory=dict)
    instructions: int = 0

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        with _isolated(self.root / "src", "chip8"):
            import chip8 as islay_chip8

        with tempfile.TemporaryDirectory() as tmp:
            rom_path = Path(tmp) / "rom.ch8"
            rom_path.write_bytes(rom)
            machine = islay_chip8.Chip8()
            machine.load_data(str(self.root / "font_set"), 0)
            machine.load_data(str(rom_path), 512)

            self.instructions = 0
            out: list[Frame] = []
            for _ in range(count):
                for _ in range(CYCLES_PER_FRAME):
                    machine.cycle()
                    self.instructions += 1
                machine.update_timers()
                out.append(bytes(1 if p else 0 for p in machine.display))
            return out


@dataclass
class robertolaru_adapter:
    """robertolaru/chip8py. CPU() with cycle() and a flat bytearray display."""

    root: Path
    name: str = "robertolaru"
    quirks: dict = field(default_factory=dict)
    instructions: int = 0

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        _stub_pygame()
        with _isolated(self.root, "cpu", "constants", "main"):
            from cpu import CPU

            machine = CPU()
            machine.load_bin(rom)
            machine.pc = 0x200  # their __init__ leaves pc at 0; the front-end sets it

            self.instructions = 0
            out: list[Frame] = []
            for _ in range(count):
                for _ in range(CYCLES_PER_FRAME):
                    machine.cycle()
                    self.instructions += 1
                out.append(bytes(1 if p else 0 for p in machine.display))
            return out


@dataclass
class cwithmichael_adapter:
    """cwithmichael/chip8_py. Cpu() with reset() then cycle(); gfx is a flat list of bools."""

    root: Path
    name: str = "cwithmichael"
    quirks: dict = field(default_factory=dict)
    instructions: int = 0

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        _stub_pygame()
        with _isolated(self.root, "cpu", "chip8", "main"):
            from cpu import Cpu

            machine = Cpu()
            machine.reset()  # sets pc=0x200 and loads the fontset; the constructor does neither
            for offset, byte in enumerate(rom):
                machine.memory[0x200 + offset] = byte

            self.instructions = 0
            out: list[Frame] = []
            for _ in range(count):
                for _ in range(CYCLES_PER_FRAME):
                    machine.cycle()
                    self.instructions += 1
                out.append(bytes(1 if p else 0 for p in machine.gfx))
            return out


@dataclass
class rudzen_adapter:
    """rudzen/Chip8Py. A Chip8 state dataclass driven by static Cpu.load_program/step.

    Their step() consults time.time() to pace 60Hz timer updates, so timer behaviour depends on
    wall clock. No ROM in the study is timer-dependent (Amendment 2 rule 3 excludes those), and
    the determinism test covers the rest.
    """

    root: Path
    name: str = "rudzen"
    quirks: dict = field(default_factory=dict)
    instructions: int = 0

    def frames(self, rom: bytes, count: int) -> list[Frame]:
        with _isolated(self.root, "cpu", "chip8", "common", "sdl_wrapper", "main"):
            from chip8 import Chip8
            from cpu import Cpu

            state = Chip8()
            Cpu.load_program(state, list(rom))
            cpu = Cpu()

            self.instructions = 0
            out: list[Frame] = []
            for _ in range(count):
                for _ in range(CYCLES_PER_FRAME):
                    cpu.step(state, CYCLES_PER_FRAME)
                    self.instructions += 1
                out.append(bytes(1 if p else 0 for p in state.gfx))
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
    "cwithmichael_adapter": cwithmichael_adapter,
    "islay_adapter": islay_adapter,
    "robertolaru_adapter": robertolaru_adapter,
    "rudzen_adapter": rudzen_adapter,
    "wyattferguson_adapter": wyattferguson_adapter,
}


def build(entry: Entry, root: Path, **kwargs):
    """Instantiate the adapter an entry names."""
    return ADAPTERS[entry.adapter](root=root, name=entry.key, **kwargs)
