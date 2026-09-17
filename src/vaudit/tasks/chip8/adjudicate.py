"""Read what the correctness ROMs REPORT, rather than whether a frame matches mine.

Comparing frames answers "does this interpreter agree with my reference", which is not the
question. My reference could be the wrong one, and an implementation that disagrees with it may
be right. Excluding someone from the population on that basis would bake my own bugs into the
study's definition of correct.

corax+ and flags both render a per-test mark, and the marks are the ROM's own verdict:

    OK   #.#     ERR  #.#
         ##.          .#.
         #..          #.#

(`image-ok`/`image-no` in 3-corax+.8o and `flag-ok`/`flag-err` in utils/text-rendering.8o — the
same two glyphs, drawn with a leading blank row in corax+.)

So eligibility is decided by counting ERR marks in the final frame. An interpreter with zero is
correct by the suite's own account, whatever my reference thinks; one with any is wrong, and
including it would turn its bug into a fairness finding of mine.
"""

from __future__ import annotations

from dataclasses import dataclass

from .harness import HEIGHT, WIDTH, Frame

OK_MARK = ((1, 0, 1), (1, 1, 0), (1, 0, 0))
ERR_MARK = ((1, 0, 1), (0, 1, 0), (1, 0, 1))


def _matches(frame: Frame, x: int, y: int, pattern) -> bool:
    for dy, row in enumerate(pattern):
        for dx, want in enumerate(row):
            if frame[(y + dy) * WIDTH + (x + dx)] != want:
                return False
    return True


def count_marks(frame: Frame) -> tuple[int, int]:
    """(ok, err) marks in a frame. Scans every position; the glyphs are distinctive enough that
    a stray match would have to reproduce all nine pixels exactly."""
    ok = err = 0
    for y in range(HEIGHT - 2):
        for x in range(WIDTH - 2):
            if _matches(frame, x, y, OK_MARK):
                ok += 1
            elif _matches(frame, x, y, ERR_MARK):
                err += 1
    return ok, err


def mark_map(frame: Frame) -> dict[tuple[int, int], str]:
    """Every position showing a mark, and which one.

    This scans the whole frame and therefore includes false positives: the ERR glyph
    (#.# / .#. / #.#) also occurs inside the opcode-label text these ROMs print, which is why
    raw totals are not a verdict. Those hits are identical in every frame, so they cancel in
    `disagreements` below — which is the only thing this is used for.
    """
    found = {}
    for y in range(HEIGHT - 2):
        for x in range(WIDTH - 2):
            if _matches(frame, x, y, OK_MARK):
                found[(x, y)] = "ok"
            elif _matches(frame, x, y, ERR_MARK):
                found[(x, y)] = "err"
    return found


def disagreements(frames: dict[str, Frame]) -> dict[tuple[int, int], dict[str, str]]:
    """Positions where interpreters show DIFFERENT marks, with who shows what.

    Static text is identical everywhere, so a position only appears here if the ROM rendered a
    different verdict for someone. No layout constants and no assumption that my reference is
    right: the ROM decided, and this reports what it decided about whom.
    """
    maps = {name: mark_map(f) for name, f in frames.items()}
    positions = {p for m in maps.values() for p in m}
    out = {}
    for position in sorted(positions):
        shown = {name: m.get(position, "-") for name, m in maps.items()}
        if len(set(shown.values())) > 1:
            out[position] = shown
    return out


def failures_against_peers(frames: dict[str, Frame]) -> dict[str, int]:
    """How many tests each interpreter fails that some other interpreter passes.

    The eligibility rule. Zero means nothing in this population contradicts it; more than zero
    means the ROM itself reported a failure that others did not have — wrong, not different.
    """
    counts = dict.fromkeys(frames, 0)
    for shown in disagreements(frames).values():
        if "ok" not in shown.values():
            continue  # nobody passed it; not evidence against any one of them
        for name, mark in shown.items():
            if mark != "ok":
                counts[name] += 1
    return counts


@dataclass(frozen=True)
class Verdict:
    interpreter: str
    rom: str
    ok: int
    err: int

    @property
    def total(self) -> int:
        return self.ok + self.err

    @property
    def correct(self) -> bool:
        """The ROM reported no failures. Zero marks at all is NOT a pass — it means the ROM never
        rendered its results, which is a failure to run, not a clean sheet."""
        return self.total > 0 and self.err == 0

    def render(self) -> str:
        state = "CORRECT" if self.correct else ("FAILS" if self.total else "NO OUTPUT")
        return f"{self.interpreter:<16} {self.rom:<10} ok={self.ok:>3} err={self.err:>3}  {state}"


def adjudicate(interpreter_name: str, rom_name: str, frame: Frame) -> Verdict:
    ok, err = count_marks(frame)
    return Verdict(interpreter=interpreter_name, rom=rom_name, ok=ok, err=err)
