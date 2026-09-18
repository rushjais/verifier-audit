"""Where §4.6's regime ends — PREDICTIONS.md Amendment 8.

§4.6 shows that three grading strategies score a blank frame above a correct-but-divergent one,
and then admits in its scope paragraph that nothing measures how far that generalises. A reader's
first objection is that the effect is an artefact of a nearly-empty 64x32 display, where the blank
frame is already 99.3% pixel-correct before any metric runs.

This module answers that objection and nothing else. **It is synthetic.** There is no interpreter
and no ROM in it, it never touches the population, and its frames are generated from a fixed seed.

Two parameters govern it, not one. Let `d` be the lit fraction and `phi` the fraction of the lit
content the divergence MOVES. Amendment 8 first registered `phi > 0.5`, "independent of density",
and that was **wrong** — it dropped the collision term, because content that moves does not always
land on dark pixels. Amendment 10 corrects it:

    blank frame       differs in  d*N                pixels
    displaced frame   differs in  2*phi*d*N*(1-d)    the (1-d) is the free landing sites

    blank scores higher under pixel proportion  <=>  phi*(1-d) > 1/2

so the boundary is the curve `phi* = 1/(2*(1-d))`, which leaves the unit square at `d = 0.5`:
above half-lit, no amount of movement lets a blank frame win. §4.6 sits in the far corner —
`d = 14/2048 = 0.0068` and `phi = 1` — where the collision term is negligible, which is exactly
why the wrong derivation looked right there.

SSIM does not inherit that curve. It pools over blocks, so it never sees global density; it sees
block occupancy. Held at identical lit count, a frame with content in 19 blocks and one with the
same content in 600 give pixel proportion the same score and SSIM scores 350x apart.

`strategies.py` is hardcoded to 64x32, so the dimension-general versions live here. New code is a
new place for a defect, which is incident pattern C, so `agrees_with_strategies()` checks them
against the originals on the real ROM frames and the study refuses to run if they disagree.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# --- the five strategies, on arbitrary 2-D arrays in [0, 1] -----------------------------------
#
# Same arithmetic as strategies.py, with HEIGHT/WIDTH lifted out. Any divergence between the two
# is a bug in one of them, which is what the equivalence check exists to catch.


def a_exact(ref: np.ndarray, cand: np.ndarray) -> float:
    return 1.0 if np.array_equal(ref, cand) else 0.0


def a_pixel_proportion(ref: np.ndarray, cand: np.ndarray) -> float:
    return float((ref == cand).mean())


def a_thresholded(ref: np.ndarray, cand: np.ndarray, tau: float = 0.05) -> float:
    return 1.0 if (1.0 - a_pixel_proportion(ref, cand)) <= tau else 0.0


def _gradient_magnitude(x: np.ndarray) -> np.ndarray:
    hx = np.array([[1, 0, -1], [1, 0, -1], [1, 0, -1]]) / 3.0
    padded = np.pad(x, 1, mode="edge")
    gx = sum(
        hx[i + 1, j + 1] * padded[1 + i : 1 + i + x.shape[0], 1 + j : 1 + j + x.shape[1]]
        for i in (-1, 0, 1)
        for j in (-1, 0, 1)
    )
    gy = sum(
        hx.T[i + 1, j + 1] * padded[1 + i : 1 + i + x.shape[0], 1 + j : 1 + j + x.shape[1]]
        for i in (-1, 0, 1)
        for j in (-1, 0, 1)
    )
    return np.sqrt(gx**2 + gy**2)


def a_gmsd(ref: np.ndarray, cand: np.ndarray, c: float = 0.0026) -> float:
    gr, gc = _gradient_magnitude(ref), _gradient_magnitude(cand)
    gms = (2 * gr * gc + c) / (gr**2 + gc**2 + c)
    return float(1.0 - np.std(gms))


def a_ssim(ref: np.ndarray, cand: np.ndarray, window: int = 8) -> float:
    c1, c2 = (0.01 * 1.0) ** 2, (0.03 * 1.0) ** 2
    h, w = ref.shape
    scores = []
    for y in range(0, h, window):
        for x in range(0, w, window):
            pa, pb = ref[y : y + window, x : x + window], cand[y : y + window, x : x + window]
            ma, mb = pa.mean(), pb.mean()
            va, vb = pa.var(), pb.var()
            cov = ((pa - ma) * (pb - mb)).mean()
            scores.append(
                ((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma**2 + mb**2 + c1) * (va + vb + c2))
            )
    return float(np.mean(scores))


ARRAY_STRATEGIES = {
    "exact match": a_exact,
    "pixel proportion": a_pixel_proportion,
    "thresholded (t=.05)": a_thresholded,
    "GMSD": a_gmsd,
    "SSIM": a_ssim,
}


def agrees_with_strategies(tol: float = 1e-12) -> dict[str, float]:
    """Largest disagreement per strategy against `strategies.py`, on the real ROM frames.

    Amendment 8 requires this before the study runs. Imported lazily so this module stays usable
    without a fetched population.
    """
    import dataclasses

    from .core import CHIP48, COSMAC_VIP
    from .harness import HEIGHT, WIDTH, NativeInterpreter
    from .quirk_roms import INDEX_ROM, SHIFT_ROM, WRAP_ROM
    from .strategies import STRATEGIES

    def frame(rom: bytes, quirks) -> bytes:
        return NativeInterpreter(name="check", quirks=quirks).frames(rom, 6)[-1]

    wrap_on = dataclasses.replace(COSMAC_VIP, sprites_wrap=True)
    wrap_off = dataclasses.replace(COSMAC_VIP, sprites_wrap=False)
    pairs = [
        (frame(SHIFT_ROM, COSMAC_VIP), frame(SHIFT_ROM, CHIP48)),
        (frame(INDEX_ROM, COSMAC_VIP), frame(INDEX_ROM, CHIP48)),
        (frame(WRAP_ROM, wrap_on), frame(WRAP_ROM, wrap_off)),
    ]
    pairs += [(a, bytes(len(a))) for a, _ in pairs]  # and against the blank cheat

    worst = dict.fromkeys(STRATEGIES, 0.0)
    for ref, cand in pairs:
        ra = np.frombuffer(ref, dtype=np.uint8).reshape(HEIGHT, WIDTH).astype(np.float64)
        ca = np.frombuffer(cand, dtype=np.uint8).reshape(HEIGHT, WIDTH).astype(np.float64)
        for name, fn in STRATEGIES.items():
            delta = abs(fn(ref, cand) - ARRAY_STRATEGIES[name](ra, ca))
            worst[name] = max(worst[name], delta)
    if max(worst.values()) > tol:
        raise AssertionError(f"array strategies disagree with strategies.py: {worst}")
    return worst


# --- synthetic frames ---------------------------------------------------------------------------


def structured_frame(h: int, w: int, density: float, seed: int, cell: int = 4) -> np.ndarray:
    """A binary frame of roughly `density` lit pixels, built from `cell`-sized blocks.

    Blocks rather than per-pixel noise: white noise has no spatial structure, and SSIM's whole
    subject is structure. Real frames are made of tiles and sprites, so the synthetic stand-in is
    too. Deterministic in `seed`.
    """
    if not 0.0 <= density <= 1.0:
        raise ValueError("density must be a fraction")
    rng = np.random.default_rng(seed)
    coarse = rng.random(((h + cell - 1) // cell, (w + cell - 1) // cell)) < density
    return np.repeat(np.repeat(coarse, cell, axis=0), cell, axis=1)[:h, :w].astype(np.float64)


def move_fraction(frame: np.ndarray, phi: float, shift: int, seed: int) -> np.ndarray:
    """Displace a fraction `phi` of the frame's LIT pixels by `shift` columns.

    The moved pixels are chosen by column band so the divergence is contiguous, like a sprite or a
    scrolled layer rather than scattered speckle. Returns a frame where that band's content has
    moved and the rest is untouched.
    """
    if not 0.0 <= phi <= 1.0:
        raise ValueError("phi must be a fraction")
    lit = frame > 0
    total = int(lit.sum())
    if total == 0 or phi == 0.0:
        return frame.copy()

    # Choose the widest left-anchored column band holding <= phi of the lit content.
    per_col = lit.sum(axis=0)
    target = phi * total
    cut, running = 0, 0
    for x, n in enumerate(per_col):
        if running + n > target:
            break
        running += n
        cut = x + 1

    out = frame.copy()
    carrier = np.zeros_like(out)
    carrier[:, :cut] = out[:, :cut]  # the content that is going to move
    out[:, :cut] = 0.0  # it leaves the band
    moved = np.roll(carrier, shift, axis=1)  # and reappears `shift` columns right
    # `roll` rather than a slice assignment so nothing falls off the edge: the derivation in
    # Amendment 8 counts phi*d*N pixels vanishing and phi*d*N appearing, and content lost at the
    # boundary would break that accounting silently. Overlap with the unmoved content is left in,
    # because it is real — `Point.moved` reports the actual differing count so the gap between it
    # and 2*phi*d*N is visible rather than assumed away.
    return np.maximum(out, moved)


@dataclass(frozen=True)
class Point:
    density: float
    phi: float
    moved: int
    lit: int
    scores: dict[str, float]
    blank: dict[str, float]

    def blank_wins(self, strategy: str) -> bool:
        """Does the cheat that draws nothing outscore the correct-but-divergent frame?"""
        return self.blank[strategy] > self.scores[strategy]


def sweep_phi(
    h: int,
    w: int,
    density: float,
    phis: tuple[float, ...],
    shift: int = 8,
    seed: int = 20260917,
) -> list[Point]:
    """Scores at each moved-fraction, against the divergent frame and against a blank frame."""
    ref = structured_frame(h, w, density, seed)
    blank = np.zeros_like(ref)
    lit = int((ref > 0).sum())
    out = []
    for phi in phis:
        cand = move_fraction(ref, phi, shift, seed)
        moved = int((ref != cand).sum())
        out.append(
            Point(
                density=density,
                phi=phi,
                moved=moved,
                lit=lit,
                scores={k: f(ref, cand) for k, f in ARRAY_STRATEGIES.items()},
                blank={k: f(ref, blank) for k, f in ARRAY_STRATEGIES.items()},
            )
        )
    return out


def crossover(points: list[Point], strategy: str) -> float | None:
    """The SMALLEST phi at which the blank frame starts outscoring the divergence, else None.

    Direction matters and is easy to get backwards: the blank frame's error is the whole lit
    content, while the divergence's grows with how much of it moves, so the cheat wins at HIGH phi.
    The crossover is therefore the lowest moved-fraction at which the cheat takes over — near 0.5
    confirms Prediction 17, and `None` means the divergence outscored the cheat throughout.
    """
    winning = [p.phi for p in points if p.blank_wins(strategy)]
    return min(winning) if winning else None


def concentrated_frame(h: int, w: int, lit: int, block: int = 8, seed: int = 0) -> np.ndarray:
    """`lit` lit pixels packed into as few `block`-sized blocks as possible.

    The partner of `spread_frame`: same content, minimum block occupancy. Prediction 23 turns on
    the difference between them, so they must agree on lit count exactly.
    """
    out = np.zeros((h, w), dtype=np.float64)
    placed = 0
    for by in range(0, h, block):
        for bx in range(0, w, block):
            if placed >= lit:
                return out
            take = min(lit - placed, block * block)
            cell = np.zeros(block * block)
            cell[:take] = 1.0
            tile = cell.reshape(block, block)
            hh, ww = min(block, h - by), min(block, w - bx)
            out[by : by + hh, bx : bx + ww] = tile[:hh, :ww]
            placed += int(tile[:hh, :ww].sum())
    return out


def spread_frame(h: int, w: int, lit: int, block: int = 8, seed: int = 0) -> np.ndarray:
    """`lit` lit pixels scattered one per block across as many blocks as possible."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), dtype=np.float64)
    blocks = [(by, bx) for by in range(0, h, block) for bx in range(0, w, block)]
    rng.shuffle(blocks)
    placed, per = 0, 1
    while placed < lit:
        for by, bx in blocks:
            if placed >= lit:
                break
            for k in range(per):
                if placed >= lit:
                    break
                y, x = by + (k // block) % block, bx + k % block
                if y < h and x < w and out[y, x] == 0.0:
                    out[y, x] = 1.0
                    placed += 1
        per += 1
        if per > block * block:
            break
    return out


def occupancy(frame: np.ndarray, block: int = 8) -> int:
    """How many `block`x`block` blocks hold at least one lit pixel — SSIM's real variable."""
    h, w = frame.shape
    return sum(
        1
        for by in range(0, h, block)
        for bx in range(0, w, block)
        if frame[by : by + block, bx : bx + block].any()
    )
