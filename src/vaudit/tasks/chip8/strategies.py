"""The five grading strategies from GBA Eval's grading-iteration post, on 64x32 frames.

Each returns a similarity in [0, 1]; higher means closer to the reference. They are scored on
SEPARATION — is there any acceptance threshold that admits every eligible correct interpreter and
rejects every cheat — rather than on a rate at one chosen threshold, which would let the threshold
decide the result (PREDICTIONS.md Amendment 4).

The originals operate on 240x160 colour frames of a GBA; these operate on 64x32 monochrome. That
difference is the whole point of Prediction 13: GMSD's reported failure was sparse single-pixel
noise that the eye integrates out, and a display with no antialiasing has no such regime.
"""

from __future__ import annotations

import numpy as np

from .harness import HEIGHT, WIDTH, Frame


def _grid(frame: Frame) -> np.ndarray:
    return np.frombuffer(frame, dtype=np.uint8).reshape(HEIGHT, WIDTH).astype(np.float64)


def exact_match(reference: Frame, candidate: Frame) -> float:
    """GBA Eval's first attempt: any divergence at all is total failure."""
    return 1.0 if reference == candidate else 0.0


def pixel_proportion(reference: Frame, candidate: Frame) -> float:
    """Their second attempt: the fraction of pixels that agree."""
    a, b = _grid(reference), _grid(candidate)
    return float((a == b).mean())


def thresholded(reference: Frame, candidate: Frame, tau: float = 0.05) -> float:
    """Their third: exact matching with a tolerance. Binary at a given tau."""
    return 1.0 if (1.0 - pixel_proportion(reference, candidate)) <= tau else 0.0


def _gradient_magnitude(x: np.ndarray) -> np.ndarray:
    """Prewitt gradient magnitude, as GMSD is defined."""
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


def gmsd(reference: Frame, candidate: Frame, c: float = 0.0026) -> float:
    """Their fourth: gradient magnitude similarity, pooled by standard deviation.

    Returned as a similarity (1 - GMSD) so every strategy points the same way. Pooling by
    deviation is what made a frame of sparse speckle score like one big defect in their data.
    """
    gr, gc = _gradient_magnitude(_grid(reference)), _gradient_magnitude(_grid(candidate))
    gms = (2 * gr * gc + c) / (gr**2 + gc**2 + c)
    return float(1.0 - np.std(gms))


def ssim(reference: Frame, candidate: Frame, window: int = 8) -> float:
    """Their fifth, and what they shipped: structural similarity over local blocks.

    Blocks rather than a Gaussian window, matching the post's description ("divides each frame
    into blocks and compares the reference and candidate on average brightness, contrast, and
    correlation within each block"). Single-scale: 64x32 pixel art has no content below native
    resolution, which is why they rejected MS-SSIM.
    """
    a, b = _grid(reference), _grid(candidate)
    c1, c2 = (0.01 * 1.0) ** 2, (0.03 * 1.0) ** 2
    scores = []
    for y in range(0, HEIGHT, window):
        for x in range(0, WIDTH, window):
            pa = a[y : y + window, x : x + window]
            pb = b[y : y + window, x : x + window]
            ma, mb = pa.mean(), pb.mean()
            va, vb = pa.var(), pb.var()
            cov = ((pa - ma) * (pb - mb)).mean()
            scores.append(
                ((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma**2 + mb**2 + c1) * (va + vb + c2))
            )
    return float(np.mean(scores))


STRATEGIES = {
    "exact match": exact_match,
    "pixel proportion": pixel_proportion,
    "thresholded (t=.05)": thresholded,
    "GMSD": gmsd,
    "SSIM": ssim,
}


def separates(correct: list[float], cheats: list[float]) -> float | None:
    """The acceptance threshold that admits every correct candidate and rejects every cheat.

    Returns the midpoint of the admitting range, or None when no threshold does both — which is
    the interesting answer, and the one Prediction 11 expects for pixel proportion.
    """
    if not correct or not cheats:
        return None
    floor, ceiling = min(correct), max(cheats)
    return (floor + ceiling) / 2 if floor > ceiling else None
