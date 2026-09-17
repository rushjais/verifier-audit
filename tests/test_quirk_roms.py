"""ROM A and its acceptance gates (PREDICTIONS.md Amendment 3)."""

import pytest

from vaudit.tasks.chip8.adapters import build
from vaudit.tasks.chip8.fetch import is_fetched, path_for
from vaudit.tasks.chip8.manifest import usable_population
from vaudit.tasks.chip8.quirk_roms import (
    INDEX_ROM,
    INDEX_TARGET,
    SHIFT_ROM,
    SHIFT_TARGET,
    check,
)

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
    assert result.sensitive_to_target, f"flipping {SHIFT_TARGET} must change the frame"
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


# --- ROM B -------------------------------------------------------------------------------------


def test_rom_b_gates_one_to_three_hold():
    result = check(INDEX_ROM, frames=30, target=INDEX_TARGET)
    assert result.timer_free
    assert result.sensitive_to_target, f"flipping {INDEX_TARGET} must change the frame"
    assert not result.spurious, f"other quirks changed the frame: {result.spurious}"
    assert result.settles_at is not None


def test_rom_b_substitutes_a_glyph_rather_than_moving_one():
    """The contrast with ROM A, and the reason Prediction 14 could be tested at all."""
    from vaudit.tasks.chip8.core import COSMAC_VIP, Quirks
    from vaudit.tasks.chip8.harness import NativeInterpreter

    vip = NativeInterpreter("vip", COSMAC_VIP).frames(INDEX_ROM, 30)[-1]
    c48 = NativeInterpreter("c48", Quirks(memory_increments_i=False)).frames(INDEX_ROM, 30)[-1]
    assert vip != c48
    assert sum(vip) == sum(c48) == 14, "both draw a 14-pixel glyph"
    lit = lambda f: {i % 64 for i, p in enumerate(f) if p}  # noqa: E731
    assert lit(vip) & lit(c48), "same columns — substituted in place, not relocated"


@needs_population
def test_rom_b_gate_four_and_a_different_population_split():
    """Interpreters mix quirk choices: the ROM A and ROM B splits are not the same partition."""
    b = {e.key: build(e, path_for(e)).frames(INDEX_ROM, 30)[-1] for e in _fetched}
    result = check(INDEX_ROM, third_party=b, frames=30, target=INDEX_TARGET)
    assert result.accepted

    a = {e.key: build(e, path_for(e)).frames(SHIFT_ROM, 30)[-1] for e in _fetched}
    ref = "craigthomas"
    like_ref_on_a = {k for k, f in a.items() if f == a[ref]}
    like_ref_on_b = {k for k, f in b.items() if f == b[ref]}
    assert like_ref_on_a != like_ref_on_b, (
        "if the two splits matched, 'VIP-like' would be a property of an implementation"
    )
