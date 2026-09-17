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

from .core import COSMAC_VIP, Quirks
from .harness import WIDTH, NativeInterpreter

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

# --- ROM B: the FX55/FX65 index quirk, per Amendment 3 ----------------------------------------
#
#   0x200  A220   I = 0x220          ; data area inside the ROM image
#   0x202  6000   V0 = 0
#   0x204  F055   store V0 at I      ; VIP: I becomes 0x221.  CHIP-48: I stays 0x220.
#   0x206  F065   load  V0 from I    ; VIP reads 0x221 (= 3). CHIP-48 reads 0x220 (= 0, just stored)
#   0x208  F029   I = font(V0)
#   0x20A  6100   V1 = 0
#   0x20C  6200   V2 = 0
#   0x20E  D125   draw glyph at (V1, V2), 5 rows
#   0x210  1210   jump self
#   ...    pad
#   0x220  00     scratch — overwritten by the store
#   0x221  03     the digit the VIP behaviour reaches
#
# The two behaviours draw DIFFERENT DIGITS at the SAME position: '0' and '3', both 14 lit pixels.
# That is the complement of ROM A, where one glyph MOVES. Same-block structural change versus
# cross-block relocation — which is exactly the distinction block SSIM is sensitive to.
_INDEX_CODE = [
    0xA2,
    0x20,
    0x60,
    0x00,
    0xF0,
    0x55,
    0xF0,
    0x65,
    0xF0,
    0x29,
    0x61,
    0x00,
    0x62,
    0x00,
    0xD1,
    0x25,
    0x12,
    0x10,
]
INDEX_ROM = bytes(_INDEX_CODE + [0x00] * (0x20 - len(_INDEX_CODE)) + [0x00, 0x03])

INDEX_ROM_SOURCE = """\
# digit.8o — isolates the FX55/FX65 index quirk. Assembles to the bytes in INDEX_ROM.
: main
  i := 0x220
  v0 := 0
  save v0        # VIP leaves i advanced to 0x221; CHIP-48 leaves it at 0x220
  load v0        # so this reads a different byte under each behaviour
  i := hex v0
  v1 := 0
  v2 := 0
  sprite v1 v2 5
  loop again
"""


def shift_rom(v1: int, v2: int) -> bytes:
    """ROM A generalised: `V1 = v1`, `V2 = v2`, then 8126.

    The VIP behaviour draws the glyph at `v2 >> 1`, CHIP-48 at `v1 >> 1`, so the pair sets the
    displacement between the two correct renderings. Everything else — glyph, row, instruction
    count — is identical to ROM A. Amendment 6 uses this to test whether SSIM's failure tracks
    distance or block count.
    """
    if not (0 <= v1 <= 0xFF and 0 <= v2 <= 0xFF):
        raise ValueError("register values must be bytes")
    if not (v1 >> 1) < WIDTH - 4 or not (v2 >> 1) < WIDTH - 4:
        raise ValueError("both glyph positions must fit on screen without clipping")
    return bytes(
        [0x61, v1, 0x62, v2, 0x81, 0x26, 0x60, 0x00, 0xF0, 0x29, 0x63, 0x00, 0xD1, 0x35, 0x12, 0x0E]
    )


def displacement(v1: int, v2: int) -> int:
    return abs((v1 >> 1) - (v2 >> 1))


# --- ROM C: the sprite-clipping quirk, per Amendment 7 ----------------------------------------
#
#   0x200  613E   V1 = 62        ; x, hard against the right edge
#   0x202  6200   V2 = 0         ; y
#   0x204  6000   V0 = 0         ; digit 0
#   0x206  F029   I  = font(V0)
#   0x208  D125   draw glyph at (V1, V2), 5 rows
#   0x20A  120A   jump self
#
# Wrapping puts the overflowing columns at x=0; clipping does not draw them. A THIRD kind of
# divergence — partial addition, not relocation and not substitution — with ROM B's one-block
# geometry. Amendment 7 uses it to separate "kind matters" from "block count matters".
WRAP_ROM = bytes([0x61, 0x3E, 0x62, 0x00, 0x60, 0x00, 0xF0, 0x29, 0xD1, 0x25, 0x12, 0x0A])

WRAP_ROM_SOURCE = """\
# wrap.8o — isolates the sprite-clipping quirk. Assembles to the bytes in WRAP_ROM.
: main
  v1 := 62       # hard against the right edge
  v2 := 0
  v0 := 0
  i := hex v0
  sprite v1 v2 5 # wrapping interpreters continue at x=0; clipping ones stop
  loop again
"""

SHIFT_TARGET = "shift_uses_vy"
INDEX_TARGET = "memory_increments_i"
WRAP_TARGET = "sprites_wrap"
ALL_QUIRKS = ("shift_uses_vy", "memory_increments_i", "jump_uses_vx", "vf_reset", "sprites_wrap")


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


def check(
    rom: bytes,
    third_party: dict[str, bytes] | None = None,
    frames: int = 30,
    target: str = SHIFT_TARGET,
) -> Acceptance:
    """Run the four acceptance gates. `third_party` maps interpreter name -> its final frame."""
    base = _frame(rom, COSMAC_VIP, frames)
    others = tuple(q for q in ALL_QUIRKS if q != target)
    flipped = Quirks(**{target: not getattr(COSMAC_VIP, target)})

    timer_free = base == _frame(rom, COSMAC_VIP, frames, tick=False)
    sensitive = _frame(rom, flipped, frames) != base
    spurious = tuple(
        q for q in others if _frame(rom, Quirks(**{q: not getattr(COSMAC_VIP, q)}), frames) != base
    )
    insensitive = tuple(q for q in others if q not in spurious)

    settles_at = None
    for n in range(2, frames):
        if _frame(rom, COSMAC_VIP, n) == base:
            settles_at = n
            break

    reproduced: tuple[str, ...] = ()
    if third_party:
        expected = (base, _frame(rom, flipped, frames))
        reproduced = tuple(name for name, frame in third_party.items() if frame in expected)

    return Acceptance(
        timer_free=timer_free,
        sensitive_to_target=sensitive,
        insensitive_to_others=insensitive,
        spurious=spurious,
        settles_at=settles_at,
        third_party_reproduced=reproduced,
    )
