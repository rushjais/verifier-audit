"""The Amendment 8 study's own gates. If these fail, the regime numbers are not trustworthy."""

from __future__ import annotations

import numpy as np
import pytest

from vaudit.tasks.chip8.regime import (
    ARRAY_STRATEGIES,
    agrees_with_strategies,
    concentrated_frame,
    crossover,
    move_fraction,
    occupancy,
    spread_frame,
    structured_frame,
    sweep_phi,
)


def test_array_strategies_agree_with_the_shipped_ones():
    """Amendment 8's precondition: new code must reproduce `strategies.py` exactly.

    Needs the fetched population, since it scores the real ROM frames.
    """
    pytest.importorskip("numpy")
    try:
        worst = agrees_with_strategies()
    except (FileNotFoundError, ImportError) as exc:  # population absent
        pytest.skip(f"population not fetched: {exc}")
    assert max(worst.values()) <= 1e-12, worst


def test_structured_frame_hits_its_density_and_is_deterministic():
    a = structured_frame(160, 240, 0.25, seed=1)
    b = structured_frame(160, 240, 0.25, seed=1)
    assert np.array_equal(a, b), "same seed must give the same frame"
    assert not np.array_equal(a, structured_frame(160, 240, 0.25, seed=2))
    assert abs(a.mean() - 0.25) < 0.03, a.mean()


def test_structured_frame_has_spatial_structure():
    """Not white noise: neighbouring pixels must correlate, because SSIM's subject is structure."""
    f = structured_frame(160, 240, 0.3, seed=7, cell=4)
    same_as_right = (f[:, :-1] == f[:, 1:]).mean()
    assert same_as_right > 0.7, same_as_right


def test_move_fraction_conserves_lit_content():
    """`roll`, not a slice: nothing may fall off the edge, or Amendment 8's accounting breaks."""
    ref = structured_frame(32, 64, 0.1, seed=3)
    for phi in (0.25, 0.5, 1.0):
        moved = move_fraction(ref, phi, shift=8, seed=3)
        assert moved.sum() <= ref.sum(), "displacement cannot create content"
        # Overlap can only reduce the count, and only by the overlapping amount.
        assert moved.sum() >= ref.sum() * 0.5, (phi, moved.sum(), ref.sum())


def test_move_fraction_at_phi_zero_changes_nothing():
    ref = structured_frame(32, 64, 0.2, seed=4)
    assert np.array_equal(move_fraction(ref, 0.0, shift=8, seed=4), ref)


def test_moved_pixel_count_rises_with_phi():
    """The independent variable has to actually vary, or a flat result means nothing."""
    pts = sweep_phi(32, 64, 0.1, (0.1, 0.3, 0.6, 1.0))
    counts = [p.moved for p in pts]
    assert counts == sorted(counts), counts
    assert counts[0] < counts[-1]


def test_crossover_returns_the_smallest_phi_where_the_cheat_wins():
    """Direction is easy to invert; this pins it. The cheat wins at HIGH phi."""
    pts = sweep_phi(32, 64, 0.10, (0.05, 0.5, 0.6, 0.9, 1.0))
    cx = crossover(pts, "pixel proportion")
    assert cx is not None
    winning = [p.phi for p in pts if p.blank_wins("pixel proportion")]
    assert cx == min(winning)
    assert all(p.phi >= cx or not p.blank_wins("pixel proportion") for p in pts)


def test_blank_frame_scores_worse_as_density_rises():
    """The mechanism behind Prediction 18's failure, asserted so a regression would show up.

    A blank frame has zero variance, which collapses SSIM's luminance and contrast terms in every
    non-empty block — so the denser the reference, the worse the blank cheat does.
    """
    blank_ssim = []
    for d in (0.05, 0.25, 0.50):
        ref = structured_frame(160, 240, d, seed=11)
        blank_ssim.append(ARRAY_STRATEGIES["SSIM"](ref, np.zeros_like(ref)))
    assert blank_ssim == sorted(blank_ssim, reverse=True), blank_ssim
    assert blank_ssim[0] > 0.5 and blank_ssim[-1] < 0.2, blank_ssim


def test_one_displaced_sprite_at_gba_scale_beats_the_blank_cheat():
    """Prediction 19, as a standing assertion: the sparse-frame regime does not reach here."""
    pts = sweep_phi(160, 240, 0.25, (0.01,), shift=8)
    p = pts[0]
    for strategy in ("pixel proportion", "SSIM", "GMSD"):
        assert not p.blank_wins(strategy), (strategy, p.scores[strategy], p.blank[strategy])


def test_concentrated_and_spread_frames_hold_lit_count_but_differ_in_occupancy():
    """Prediction 23's whole design: same content, opposite block layouts."""
    c = concentrated_frame(160, 240, 1200)
    s = spread_frame(160, 240, 1200)
    assert int(c.sum()) == int(s.sum()) == 1200
    assert occupancy(c) < 25 < 500 < occupancy(s)


def test_block_occupancy_and_not_density_controls_ssim():
    """The confirmed half of Prediction 23, pinned as a regression.

    Identical lit count, so pixel proportion scores the blank cheat identically against both; SSIM
    scores it wildly differently, because a 19-block frame leaves most blocks empty and matching.
    """
    c, s = concentrated_frame(160, 240, 1200), spread_frame(160, 240, 1200)
    pp_c = ARRAY_STRATEGIES["pixel proportion"](c, np.zeros_like(c))
    pp_s = ARRAY_STRATEGIES["pixel proportion"](s, np.zeros_like(s))
    assert abs(pp_c - pp_s) < 1e-12, (pp_c, pp_s)

    ssim_c = ARRAY_STRATEGIES["SSIM"](c, np.zeros_like(c))
    ssim_s = ARRAY_STRATEGIES["SSIM"](s, np.zeros_like(s))
    assert ssim_c > 0.9 and ssim_s < 0.01, (ssim_c, ssim_s)


def test_the_corrected_boundary_beats_a_constant_on_the_registered_grid():
    """Amendment 10's curve against Amendment 8's flat 0.5, where they actually differ."""
    pts = sweep_phi(160, 240, 0.30, tuple(round(0.40 + 0.02 * i, 2) for i in range(31)))
    obs = crossover(pts, "pixel proportion")
    assert obs is not None
    assert abs(obs - 1 / (2 * (1 - 0.30))) < 0.04, obs
    assert obs > 0.60, f"a density-independent phi=0.5 boundary would predict ~0.5, got {obs}"


# --- Amendment 9: ROM D and ROM E ---------------------------------------------------------------


def test_rom_d_and_e_isolate_their_target_quirk_and_nothing_else():
    """Gates 1-3, which need no population."""
    from vaudit.tasks.chip8.quirk_roms import (
        JUMP_ROM,
        JUMP_TARGET,
        VFRESET_ROM,
        VFRESET_TARGET,
        check,
    )

    for rom, target in ((JUMP_ROM, JUMP_TARGET), (VFRESET_ROM, VFRESET_TARGET)):
        got = check(rom, target=target)
        assert got.timer_free, target
        assert got.sensitive_to_target, target
        assert not got.spurious, (target, got.spurious)
        assert got.settles_at is not None, target


def test_rom_d_relocates_and_rom_e_substitutes():
    """Predictions 20 and 21 turn on the geometry, so pin the geometry itself."""
    from vaudit.tasks.chip8.core import CHIP48, COSMAC_VIP
    from vaudit.tasks.chip8.harness import WIDTH, NativeInterpreter
    from vaudit.tasks.chip8.quirk_roms import JUMP_ROM, VFRESET_ROM

    def cols(rom, quirks):
        f = NativeInterpreter("t", quirks).frames(rom, 30)[-1]
        lit = [x for y in range(32) for x, v in enumerate(f[y * WIDTH : (y + 1) * WIDTH]) if v]
        return (min(lit), max(lit)), sum(1 for b in f if b)

    d_ref, d_div = cols(JUMP_ROM, COSMAC_VIP), cols(JUMP_ROM, CHIP48)
    assert d_ref == ((4, 7), 14) and d_div == ((16, 19), 14), (d_ref, d_div)
    assert d_div[0][0] - d_ref[0][0] == 12, "must clear the 8-wide block, or it is not relocation"

    e_ref, e_div = cols(VFRESET_ROM, COSMAC_VIP), cols(VFRESET_ROM, CHIP48)
    assert e_ref[0] == e_div[0] == (0, 3), (e_ref, e_div)
    assert e_ref[1] == e_div[1] == 14, "substitution keeps the lit count and the position"


def test_acceptance_reports_whether_the_population_actually_split():
    """Gate 5. Amendment 9 required a split in prose; the four gates never checked it."""
    from vaudit.tasks.chip8.quirk_roms import Acceptance

    unanimous = Acceptance(True, True, (), (), 2, ("a", "b"), behaviours=1)
    split = Acceptance(True, True, (), (), 2, ("a", "b"), behaviours=2)
    assert not unanimous.population_splits
    assert split.population_splits
    # Incident #20: this used to assert `unanimous.accepted`. A ROM the whole population agrees
    # on cannot produce a data point, so it must not be accepted.
    assert not unanimous.accepted, "a non-splitting ROM tests nothing and must be rejected"
    assert split.accepted

    # Gate 4 is necessary but not sufficient: a unanimous population satisfies it trivially,
    # because every member reproduces one of the two expected frames — the same one.
    assert len(unanimous.third_party_reproduced) >= 2, "gate 4 alone would have passed this"

    # And acceptance is not decidable without running the population.
    assert not Acceptance(True, True, (), (), 2, ("a", "b"), behaviours=0).accepted
