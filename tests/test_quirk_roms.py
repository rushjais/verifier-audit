"""ROM A and its acceptance gates (PREDICTIONS.md Amendment 3)."""

import pytest

from vaudit.tasks.chip8.adapters import build
from vaudit.tasks.chip8.fetch import is_fetched, path_for
from vaudit.tasks.chip8.manifest import usable_population
from vaudit.tasks.chip8.quirk_roms import SHIFT_ROM, TARGET_QUIRK, check

_fetched = [e for e in usable_population() if is_fetched(e)]
needs_population = pytest.mark.skipif(not _fetched, reason="population not fetched")


def test_the_rom_matches_the_bytes_registered_in_amendment_3():
    """Amendment 3 fixed these opcodes before the ROM existed. They must not drift."""
    assert SHIFT_ROM == bytes(
        [
            0x61,
            0x10,
            0x62,
            0x08,
            0x81,
            0x26,
            0x60,
            0x00,
            0xF0,
            0x29,
            0x63,
            0x00,
            0xD1,
            0x35,
            0x12,
            0x0E,
        ]
    )
    assert len(SHIFT_ROM) == 16


def test_gates_one_to_three_hold_without_the_population():
    result = check(SHIFT_ROM, frames=30)
    assert result.timer_free, "a timer-dependent ROM is excluded (Amendment 2 rule 3)"
    assert result.sensitive_to_target, f"flipping {TARGET_QUIRK} must change the frame"
    assert not result.spurious, f"other quirks changed the frame: {result.spurious}"
    assert result.settles_at is not None, "the result must not depend on how long it runs"


@needs_population
def test_gate_four_third_party_interpreters_reproduce_the_divergence():
    """A ROM that only works on my own reference is a ROM that tests my reference."""
    third = {e.key: build(e, path_for(e)).frames(SHIFT_ROM, 30)[-1] for e in _fetched}
    result = check(SHIFT_ROM, third_party=third, frames=30)
    assert len(result.third_party_reproduced) >= 2
    assert result.accepted


@needs_population
def test_the_population_genuinely_splits_on_the_quirk():
    """Both behaviours must be present, or there is nothing for a strategy to rank."""
    positions = {}
    for entry in _fetched:
        frame = build(entry, path_for(entry)).frames(SHIFT_ROM, 30)[-1]
        assert sum(frame) == 14, f"{entry.key} did not draw the glyph"
        positions[entry.key] = min(i % 64 for i, p in enumerate(frame) if p)
    assert set(positions.values()) == {4, 8}, f"expected both x=4 and x=8, got {positions}"
    assert sum(1 for x in positions.values() if x == 4) >= 1
    assert sum(1 for x in positions.values() if x == 8) >= 1
