"""Authored quirk ROMs, specified in PREDICTIONS.md Amendment 3 before these bytes existed.

A ROM is an INPUT, not a population member. The interpreters are what is measured; this is what
they are measured on. The population stays third-party.

The guard against tuning an input until a chosen strategy fails is procedural and lives in the
git history: Amendment 3 fixed this design first, `accept()` below decides admission BEFORE any
grading strategy runs, and once a strategy has run the ROM is frozen. Changing it afterwards
voids the study.
"""

from __future__ import annotations

from dataclasses import dataclass

from .core import CHIP48, COSMAC_VIP, Quirks
from .harness import NativeInterpreter

# --- ROM A: the 8XY6 shift quirk, as registered -----------------------------------------------
#
#   0x200  6110   V1 = 0x10
#   0x202  6208   V2 = 0x08
#   0x204  8126   V1 = shift    ; VIP: V1 = V2>>1 = 4    CHIP-48: V1 = V1>>1 = 8
#   0x206  6000   V0 = 0        ; digit 0
#   0x208  F029   I  = font(V0) ; portable — asks the interpreter for its own font address
#   0x20A  6300   V3 = 0
#   0x20C  D135   draw glyph at (V1, V3), 5 rows
#   0x20E  120E   jump self
#
SHIFT_ROM = bytes(
    [0x61, 0x10, 0x62, 0x08, 0x81, 0x26, 0x60, 0x00, 0xF0, 0x29, 0x63, 0x00, 0xD1, 0x35, 0x12, 0x0E]
)

SHIFT_ROM_SOURCE = """\
# shift.8o — isolates the 8XY6 quirk. Assembles to the bytes in SHIFT_ROM.
: main
  v1 := 0x10
  v2 := 0x08
  v1 >>= v2      # VIP: v1 = v2>>1 = 4.  CHIP-48/SCHIP: v1 = v1>>1 = 8.
  v0 := 0
  i := hex v0    # the interpreter's OWN font address
  v3 := 0
  sprite v1 v3 5
  loop again
"""

TARGET_QUIRK = "shift_uses_vy"
OTHER_QUIRKS = ("memory_increments_i", "jump_uses_vx", "vf_reset", "sprites_wrap")


@dataclass(frozen=True)
class Acceptance:
    """The four gates from Amendment 3. A ROM enters the study only if all four hold."""

    timer_free: bool
    sensitive_to_target: bool
    insensitive_to_others: tuple[str, ...]  # quirks that (correctly) changed nothing
    spurious: tuple[str, ...]  # quirks that changed the frame but should not have
    settles_at: int | None
    third_party_reproduced: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return (
            self.timer_free
            and self.sensitive_to_target
            and not self.spurious
            and self.settles_at is not None
            and len(self.third_party_reproduced) >= 2
        )

    def render(self) -> str:
        def mark(ok: bool, detail: str = "") -> str:
            return ("PASS" if ok else "FAIL") + (f" {detail}" if detail else "")

        settled = f"at frame {self.settles_at}" if self.settles_at else ""
        return "\n".join(
            [
                f"1. timer-free               {mark(self.timer_free)}",
                f"2. sensitive to target      {mark(self.sensitive_to_target)}",
                f"   inert to the other four  {mark(not self.spurious, str(self.spurious or ''))}",
                f"3. settles                  {mark(self.settles_at is not None, settled)}",
                f"4. third-party reproduce    {mark(len(self.third_party_reproduced) >= 2)}"
                f" {list(self.third_party_reproduced)}",
                "",
                f"ACCEPTED: {self.accepted}",
            ]
        )


def _frame(rom: bytes, quirks: Quirks, frames: int, tick: bool = True) -> bytes:
    interp = NativeInterpreter("probe", quirks)
    out = interp.frames(rom, frames)
    if tick:
        return out[-1]
    # Re-run without timer ticks by driving the machine directly.
    from .core import Chip8
    from .harness import CYCLES_PER_FRAME

    machine = Chip8(quirks=quirks).load(rom)
    for _ in range(frames):
        for _ in range(CYCLES_PER_FRAME):
            machine.step()
    return bytes(machine.display)


def check(rom: bytes, third_party: dict[str, bytes] | None = None, frames: int = 30) -> Acceptance:
    """Run the four acceptance gates. `third_party` maps interpreter name -> its final frame."""
    base = _frame(rom, COSMAC_VIP, frames)

    timer_free = base == _frame(rom, COSMAC_VIP, frames, tick=False)
    sensitive = _frame(rom, Quirks(**{TARGET_QUIRK: False}), frames) != base
    spurious = tuple(
        q
        for q in OTHER_QUIRKS
        if _frame(rom, Quirks(**{q: not getattr(COSMAC_VIP, q)}), frames) != base
    )
    insensitive = tuple(q for q in OTHER_QUIRKS if q not in spurious)

    settles_at = None
    for n in range(2, frames):
        if _frame(rom, COSMAC_VIP, n) == base:
            settles_at = n
            break

    reproduced: tuple[str, ...] = ()
    if third_party:
        vip, c48 = base, _frame(rom, CHIP48, frames)
        reproduced = tuple(name for name, frame in third_party.items() if frame in (vip, c48))

    return Acceptance(
        timer_free=timer_free,
        sensitive_to_target=sensitive,
        insensitive_to_others=insensitive,
        spurious=spurious,
        settles_at=settles_at,
        third_party_reproduced=reproduced,
    )
