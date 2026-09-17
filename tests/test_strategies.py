"""The five grading strategies (PREDICTIONS.md Amendment 4)."""

import pytest

from vaudit.tasks.chip8.harness import BLANK, HEIGHT, WIDTH
from vaudit.tasks.chip8.strategies import STRATEGIES, gmsd, pixel_proportion, separates, ssim


def _frame(lit: set[tuple[int, int]]) -> bytes:
    px = bytearray(WIDTH * HEIGHT)
    for x, y in lit:
        px[y * WIDTH + x] = 1
    return bytes(px)


GLYPH = _frame({(x, y) for x in range(4, 8) for y in range(5)})
SHIFTED = _frame({(x + 4, y) for x in range(4, 8) for y in range(5)})


@pytest.mark.parametrize("name", sorted(STRATEGIES))
def test_identical_frames_score_one(name):
    assert STRATEGIES[name](GLYPH, GLYPH) == pytest.approx(1.0, abs=1e-9)


def test_pixel_proportion_scores_a_blank_screen_above_a_shifted_glyph():
    """The failure GBA Eval reported for this metric, reproduced: on a mostly-off display,
    drawing nothing beats drawing the right thing in a defensibly different place."""
    assert pixel_proportion(GLYPH, BLANK) > pixel_proportion(GLYPH, SHIFTED)


def test_ssim_scores_a_blank_screen_above_a_shifted_glyph():
    """Prediction 12. Moving structure disturbs two blocks; erasing it disturbs one."""
    assert ssim(GLYPH, BLANK) > ssim(GLYPH, SHIFTED)


def test_gmsd_is_blind_to_inversion():
    """Gradient magnitude is invariant under inversion — |grad(1-x)| == |grad(x)| — so a wholly
    inverted frame is 'perfectly similar'. Explainable, and fatal as a grader."""
    inverted = bytes(1 - p for p in GLYPH)
    assert gmsd(GLYPH, inverted) == pytest.approx(1.0, abs=1e-6)
    assert ssim(GLYPH, inverted) < 0.5


def test_separation_returns_none_when_a_cheat_outscores_a_correct_candidate():
    assert separates(correct=[0.9], cheats=[0.5]) == pytest.approx(0.7)
    assert separates(correct=[0.9], cheats=[0.95]) is None
    assert separates(correct=[], cheats=[0.1]) is None
