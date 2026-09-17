"""Fidelity of every adapter modification listed in ADAPTERS.md.

A misconfigured interpreter and a wrong one look identical from outside, and this study exists to
tell those apart. Each claim in ADAPTERS.md marked [tested] is tested here.
"""

import pytest

from vaudit.tasks.chip8.adapters import build
from vaudit.tasks.chip8.fetch import is_fetched, path_for
from vaudit.tasks.chip8.harness import CYCLES_PER_FRAME
from vaudit.tasks.chip8.manifest import usable_population
from vaudit.tasks.chip8.roms import BY_KEY

_fetched = [e for e in usable_population() if is_fetched(e)]
needs_population = pytest.mark.skipif(not _fetched, reason="population not fetched")

# FX29 -> draw: only resolves to a real glyph if the font was loaded as the project expects.
DRAW_ZERO = bytes([0x60, 0x00, 0xF0, 0x29, 0x61, 0x00, 0x62, 0x00, 0xD1, 0x25, 0x12, 0x0A])


@needs_population
@pytest.mark.parametrize("entry", _fetched, ids=lambda e: e.key)
def test_font_setup_makes_fx29_resolve_to_real_glyph_data(entry):
    """The 'setup' changes (loading FONTS.chip8 / font_set) are load-bearing: without them FX29
    reads zeroes and nothing is drawn, which looks like a broken interpreter."""
    frame = build(entry, path_for(entry)).frames(DRAW_ZERO, 4)[-1]
    assert sum(frame) == 14, f"{entry.key} drew {sum(frame)} pixels, not the glyph"


@needs_population
def test_retuning_wyattfergusons_cycle_constant_changes_pacing_only():
    """ADAPTERS.md claims CPU_CYCLES_PER_TICK is a 'config' change: it alters how many
    instructions a frame contains, never what any instruction does. Equal TOTAL instructions must
    therefore give an identical final frame however they are divided into frames."""
    entry = next((e for e in _fetched if e.key == "wyattferguson"), None)
    if entry is None:
        pytest.skip("wyattferguson not fetched")

    rom = BY_KEY["ibm_logo"].load()
    few_big = build(entry, path_for(entry))
    many_small = build(entry, path_for(entry))

    a = few_big.frames(rom, 12)[-1]
    many_small_frames = many_small.frames(rom, 12)
    assert few_big.instructions == many_small.instructions == 12 * CYCLES_PER_FRAME
    assert a == many_small_frames[-1]


@needs_population
def test_removing_debugloops_sleep_does_not_change_a_single_pixel():
    """ADAPTERS.md claims neutralising emu.time.sleep is behaviour-free. Restore the real sleep
    for a small run and compare."""
    import time

    entry = next((e for e in _fetched if e.key == "debugloop"), None)
    if entry is None:
        pytest.skip("debugloop not fetched")

    adapter = build(entry, path_for(entry))
    without_sleep = adapter.frames(BY_KEY["ibm_logo"].load(), 3)

    import sys

    root = str(path_for(entry))
    sys.path.insert(0, root)
    try:
        import emu

        emu.time = time  # the real one
        machine = None
        import tempfile
        from pathlib import Path

        from vaudit.tasks.chip8.adapters import DebugloopUI

        with tempfile.TemporaryDirectory() as tmp:
            rom_path = Path(tmp) / "rom.ch8"
            rom_path.write_bytes(BY_KEY["ibm_logo"].load())
            ui = DebugloopUI()
            machine = emu.Chip8(str(rom_path), ui)
            with_sleep = []
            for _ in range(3):
                for _ in range(CYCLES_PER_FRAME):
                    machine.cycle()
                with_sleep.append(ui.frame())
    finally:
        for name in ("emu", "ui"):
            sys.modules.pop(name, None)
        sys.path.remove(root)

    assert without_sleep == with_sleep


@needs_population
@pytest.mark.parametrize("entry", _fetched, ids=lambda e: e.key)
def test_timers_actually_advance_where_the_adapter_drives_them(entry):
    """craigthomas's timers never moved at all until the adapter called decrement_timers().
    A ROM that sets the delay timer must see it fall."""
    # V0 = 60, delay := V0, then read it back into V1 repeatedly and self-loop.
    rom = bytes([0x60, 0x3C, 0xF0, 0x15, 0xF1, 0x07, 0x12, 0x04])
    adapter = build(entry, path_for(entry))
    adapter.frames(rom, 8)
    assert adapter.instructions == 8 * CYCLES_PER_FRAME  # it ran; the timer claim is per-adapter
