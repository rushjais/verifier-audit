"""ROM A and its acceptance gates (PREDICTIONS.md Amendment 3)."""

import pytest

from vaudit.tasks.chip8.adapters import build
from vaudit.tasks.chip8.fetch import is_fetched, path_for
from vaudit.tasks.chip8.manifest import usable_population
from vaudit.tasks.chip8.quirk_roms import (
    INDEX_ROM,
    INDEX_TARGET,
    JUMP_ROM,
    JUMP_TARGET,
    SHIFT_ROM,
    SHIFT_TARGET,
    VFRESET_ROM,
    VFRESET_TARGET,
    WRAP_ROM,
    WRAP_TARGET,
    Acceptance,
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


@needs_population
def test_a_sprite_row_must_stay_on_one_scanline():
    """Neither wrapping nor clipping moves part of a sprite row to the next row. Two interpreters
    do, via a linear framebuffer index; this pins that as a defect rather than a quirk."""
    rom = bytes([0xA2, 0x0C, 0x61, 0x3E, 0x62, 0x00, 0xD1, 0x21, 0x12, 0x08, 0x00, 0x00, 0xFF])
    spilled = []
    for entry in _fetched:
        frame = build(entry, path_for(entry)).frames(rom, 20)[-1]
        if any(frame[64 + x] for x in range(64)):
            spilled.append(entry.key)
    assert set(spilled) == {"robertolaru", "cwithmichael"}, (
        f"expected exactly these two to spill onto row 1, got {spilled}"
    )


# --- incident #20: the gate that did not check what its prose said --------------------------------


def test_gate_four_b_rejects_a_rom_the_whole_population_agrees_on():
    """A non-splitting population must fail acceptance, with no population needed to prove it.

    Amendment 9 required a split in prose; the gates only asked whether two third parties
    reproduced *one of* the expected frames, which a unanimous population satisfies trivially.
    ROMs D and E passed all four that way while testing nothing.
    """
    ref = bytes([0]) * (64 * 32)
    divergent = bytearray(ref)
    divergent[0] = 1
    divergent = bytes(divergent)

    unanimous = dict.fromkeys(("a", "b", "c", "d"), ref)
    split = {"a": ref, "b": ref, "c": divergent, "d": divergent}

    for frames, expect_split in ((unanimous, False), (split, True)):
        got = Acceptance(
            timer_free=True,
            sensitive_to_target=True,
            insensitive_to_others=(),
            spurious=(),
            settles_at=2,
            third_party_reproduced=tuple(frames),
            behaviours=len(set(frames.values())),
        )
        assert got.population_splits is expect_split
        assert got.accepted is expect_split
        # gate 4 passes either way — which is exactly why 4b had to be added
        assert len(got.third_party_reproduced) >= 2


@needs_population
def test_roms_d_and_e_are_rejected_because_the_population_agrees():
    """The real fixture for the above: two ROMs that cleared four gates and test nothing."""
    for rom, target in ((JUMP_ROM, JUMP_TARGET), (VFRESET_ROM, VFRESET_TARGET)):
        third = {e.key: build(e, path_for(e)).frames(rom, 30)[-1] for e in _fetched}
        got = check(rom, third_party=third, frames=30, target=target)
        assert got.timer_free and got.sensitive_to_target and not got.spurious
        assert len(got.third_party_reproduced) >= 2, "gate 4 still passes"
        assert got.behaviours == 1, "every interpreter produces the same frame"
        assert not got.accepted, "so the ROM must not enter the study"


@needs_population
def test_roms_a_b_and_c_still_pass_the_corrected_gates():
    for rom, target, expected_behaviours in (
        (SHIFT_ROM, SHIFT_TARGET, 2),
        (INDEX_ROM, INDEX_TARGET, 2),
        (WRAP_ROM, WRAP_TARGET, 3),
    ):
        third = {e.key: build(e, path_for(e)).frames(rom, 30)[-1] for e in _fetched}
        got = check(rom, third_party=third, frames=30, target=target)
        assert got.behaviours == expected_behaviours, (target, got.behaviours)
        assert got.accepted
