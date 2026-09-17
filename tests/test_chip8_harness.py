"""M1c harness. The reference must be provably right — every number in the study rests on it."""

import pytest

from vaudit.tasks.chip8 import (
    CHIP48,
    COSMAC_VIP,
    WIDTH,
    BlankScreen,
    Chip8,
    FrozenFirstFrame,
    InvertedPalette,
    NativeInterpreter,
    OneFrameLate,
    Quirks,
    all_cheats,
    lit,
    render,
)

# Hand-assembled: V0=0, V1=0, I=font glyph "0", draw 5 rows at (V0,V1), then self-loop.
DRAW_ZERO = bytes([0x60, 0x00, 0x61, 0x00, 0xA0, 0x50, 0xD0, 0x15, 0x12, 0x08])


def _reference(**quirks):
    return NativeInterpreter(name="reference", quirks=Quirks(**quirks) if quirks else COSMAC_VIP)


def test_the_reference_draws_the_glyph_the_font_actually_encodes():
    """0xF0,0x90,0x90,0x90,0xF0 is a hollow '0'. If this is wrong, nothing downstream means
    anything."""
    frame = _reference().frames(DRAW_ZERO, 4)[-1]
    rows = render(frame).splitlines()
    assert rows[0][:8] == "####...."
    assert rows[1][:8] == "#..#...."
    assert rows[2][:8] == "#..#...."
    assert rows[3][:8] == "#..#...."
    assert rows[4][:8] == "####...."
    assert set(rows[5]) == {"."}, "nothing below the 5-row sprite"
    assert lit(frame) == 14  # 4+2+2+2+4


def test_every_run_returns_exactly_the_frames_asked_for_even_after_halting():
    """Metrics compare sequences pairwise; a short sequence would silently misalign them."""
    frames = _reference().frames(DRAW_ZERO, 12)
    assert len(frames) == 12
    assert frames[-1] == frames[-2], "a halted ROM holds its last frame"


def test_the_same_seed_gives_the_same_frames():
    rom = bytes([0xC0, 0xFF, 0x12, 0x02])  # V0 = rand & 0xFF, then self-loop
    a = NativeInterpreter("a", COSMAC_VIP, seed=7).frames(rom, 3)
    b = NativeInterpreter("b", COSMAC_VIP, seed=7).frames(rom, 3)
    assert a == b


def test_randomness_is_seeded_not_absent():
    machine_a, machine_b = Chip8(seed=1), Chip8(seed=2)
    draws_a = [machine_a._rng.randrange(256) for _ in range(8)]
    draws_b = [machine_b._rng.randrange(256) for _ in range(8)]
    assert draws_a != draws_b


# --- the quirks must actually differ, or the population has no honest variation -------------


def _run(rom: bytes, quirks: Quirks, steps: int = 12) -> Chip8:
    machine = Chip8(quirks=quirks).load(rom)
    for _ in range(steps):
        if machine.halted:
            break
        machine.step()
    return machine


def test_shift_quirk_changes_the_result():
    # V0=0b0001, V1=0b1000, then 8016 (shift). VIP shifts VY into VX; CHIP-48 shifts VX.
    rom = bytes([0x60, 0x01, 0x61, 0x08, 0x80, 0x16, 0x12, 0x06])
    assert _run(rom, COSMAC_VIP).v[0] == 0x04  # VY(8) >> 1
    assert _run(rom, Quirks(shift_uses_vy=False)).v[0] == 0x00  # VX(1) >> 1


def test_memory_quirk_changes_where_i_ends_up():
    # I=0x300, V0=0xAB, FX55 storing V0..V1.
    rom = bytes([0xA3, 0x00, 0x60, 0xAB, 0xF1, 0x55, 0x12, 0x06])
    assert _run(rom, COSMAC_VIP).i == 0x302  # advanced past what it wrote
    assert _run(rom, Quirks(memory_increments_i=False)).i == 0x300


def test_vf_reset_quirk_changes_vf():
    # VF=1, then 8011 (OR). The VIP clears VF as a side effect; CHIP-48 does not.
    rom = bytes([0x6F, 0x01, 0x60, 0x0F, 0x61, 0xF0, 0x80, 0x11, 0x12, 0x08])
    assert _run(rom, COSMAC_VIP).v[0xF] == 0
    assert _run(rom, Quirks(vf_reset=False)).v[0xF] == 1


def test_jump_quirk_changes_the_destination():
    # V0=2, V2=8, then B202. VIP adds V0; CHIP-48 adds VX where X is the high nibble.
    rom = bytes([0x60, 0x02, 0x62, 0x08, 0xB2, 0x02])
    # Exactly three instructions: the two loads and the jump. Running further would execute
    # whatever sits at the destination and the assertion would be about that instead.
    assert _run(rom, COSMAC_VIP, steps=3).pc == 0x204  # 0x202 + V0
    assert _run(rom, Quirks(jump_uses_vx=True), steps=3).pc == 0x20A  # 0x202 + V2


def test_sprite_wrap_quirk_changes_the_display():
    # Draw the glyph with V0 near the right edge: wrapping puts pixels at x=0, clipping does not.
    rom = bytes([0x60, 0x3E, 0x61, 0x00, 0xA0, 0x50, 0xD0, 0x15, 0x12, 0x08])
    clipped = _reference(sprites_wrap=False).frames(rom, 3)[-1]
    wrapped = _reference(sprites_wrap=True).frames(rom, 3)[-1]
    assert clipped != wrapped
    assert clipped[0] == 0 and wrapped[0] == 1  # column 0 only lit when wrapping


def test_the_two_named_quirk_profiles_disagree_on_a_real_rom():
    """The whole study needs correct implementations that genuinely differ on screen.

    V0=0x10, V1=0x08, then 8016. The VIP shifts VY (8 -> 4); CHIP-48 shifts VX (0x10 -> 8). The
    result is the sprite's x position, so one quirk flag moves the glyph four pixels.
    """
    rom = bytes(
        [0x60, 0x10, 0x61, 0x08, 0x80, 0x16, 0xA0, 0x50, 0x62, 0x00, 0xD0, 0x25, 0x12, 0x0C]
    )
    vip = NativeInterpreter("vip", COSMAC_VIP).frames(rom, 3)
    c48 = NativeInterpreter("chip48", CHIP48).frames(rom, 3)
    assert vip != c48, "both profiles drew the same thing; this ROM exercises no disagreement"
    assert lit(vip[-1]) == lit(c48[-1]) == 14, "both drew the glyph — just in different places"


# --- cheats ---------------------------------------------------------------------------------


@pytest.fixture
def cheats():
    return all_cheats(_reference())


def test_every_cheat_is_labelled_as_one(cheats):
    assert all(c.name.startswith("cheat:") for c in cheats)


def test_blank_screen_renders_nothing(cheats):
    frames = BlankScreen().frames(DRAW_ZERO, 5)
    assert len(frames) == 5 and all(lit(f) == 0 for f in frames)


def test_frozen_first_frame_never_changes():
    frames = FrozenFirstFrame(_reference()).frames(DRAW_ZERO, 6)
    assert len(set(frames)) == 1


def test_inverted_palette_is_structurally_identical_and_wholly_wrong():
    real = _reference().frames(DRAW_ZERO, 4)
    fake = InvertedPalette(_reference()).frames(DRAW_ZERO, 4)
    for r, f in zip(real, fake, strict=True):
        assert all(a != b for a, b in zip(r, f, strict=True))
        assert lit(f) == WIDTH * 32 - lit(r)


def test_one_frame_late_is_the_reference_shifted_by_one():
    real = _reference().frames(DRAW_ZERO, 5)
    late = OneFrameLate(_reference()).frames(DRAW_ZERO, 5)
    assert late[1:] == real[:-1]
    assert len(late) == len(real)
