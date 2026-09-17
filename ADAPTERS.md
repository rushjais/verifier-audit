# ADAPTERS.md — every change made to run someone else's interpreter

An adapter's job is to drive a third-party interpreter and read its display. Every deviation
from running that project as its author intended is listed here, because a misconfigured
interpreter and a wrong one look identical from the outside — and this study exists to measure
the difference between those two things. It has already bitten twice:

- a `pygame.key.get_pressed()` stub returning `{}` made `craigthomas` appear to crash on the
  quirks ROM. Read at face value, a working implementation would have been dropped as broken.
- `craigthomas`'s timers never advanced at all, because the adapter never called
  `decrement_timers()` — their `emulator.py` does it, their CPU does not.

Each change below is one of three kinds:

| kind | meaning |
|---|---|
| **stub** | satisfies an import or seam the project needs for a live UI that this harness never provides |
| **setup** | repeats something the project's own front-end does before running, which its CPU does not do itself |
| **config** | changes a value the project already exposes as a setting; no logic altered |

A change that would alter emulation logic is not permitted. Where one was tempting, the project
was rejected instead — see `manifest.REJECTED` (`shivrm/chip8` is the example: driving it would
have meant reimplementing its fetch loop outside its class).

Claims marked **[tested]** have a test in `tests/test_chip8_adapter_fidelity.py`.

---

## Shared by all adapters

| change | kind | why | evidence |
|---|---|---|---|
| Imports run inside `_isolated(root, *names)`, which purges colliding top-level module names before and after and restores `sys.path` | setup | Several of these projects ship a package called `chip8`. Without it, importing one hands the next that one's code, and two implementations agree perfectly because they *are* the same code — `honest_pass` reads 1.00 and the study concludes the opposite of the truth. | **[tested]** no modules or path left behind; interleaving two interpreters cannot change either one's output |
| One frame = exactly `CYCLES_PER_FRAME` instructions | config | These projects disagree about the count. Comparing a frame built from 12 instructions with one built from 15 measures pacing, not correctness. | **[tested]** every adapter reports `frames × CYCLES_PER_FRAME` executed |

**Not normalised, deliberately:** timer semantics. `craigthomas` decrements on demand,
`wyattferguson` once per `cycle()`, `debugloop` every fifth cycle via a counter it never resets
(so past the fifth, every cycle), `islay` on demand. Agreeing them would mean rewriting their
code. Consequence, stated wherever it matters: **any ROM whose final frame depends on delay-timer
pacing is not safely comparable across this population.**

---

## craigthomas/Chip8Python

| change | kind | why | evidence |
|---|---|---|---|
| `pygame` stubbed: `key.get_pressed()` returns an indexable always-false object; `mixer` discards sound; key constants are distinct integers | stub | Imported at module scope for live input and sound. No input is delivered here, so the stub is behaviourally complete. | **[tested]** every key reads not-pressed; the sixteen constants are distinct |
| `HeadlessScreen` supplies the screen API | stub | Their CPU draws through a screen object. All pixel *decisions* stay in their CPU; this only stores. | **[tested]** glyph matches the reference exactly |
| `cpu.load_rom("FONTS.chip8", 0)` before the ROM | setup | Their `emulator.py` does this; the CPU does not. Without it every `FX29` reads zeroes and nothing draws. | **[tested]** `FX29` resolves to real font data |
| `cpu.decrement_timers()` once per frame | setup | Same: their `emulator.py` does it per frame. | **[tested]** the delay timer actually advances |

## wyattferguson/chip8-emulator

| change | kind | why | evidence |
|---|---|---|---|
| `pygame` stubbed, including `display.set_mode` | stub | `Screen.__init__` opens a window. | **[tested]** as above |
| **Their** `Screen`, `Keypad`, `Audio(mute=True)` are used, not stand-ins | — | `Screen.flip_pixel` contains their wrap decision. Substituting my framebuffer would replace their behaviour with mine. | **[tested]** glyph matches the reference |
| `chip8.cpu.CPU_CYCLES_PER_TICK` retuned from 12 to `CYCLES_PER_FRAME` | config | Their `cycle()` is one 60Hz tick: timers once, then that many instructions. | **[tested]** equal *total* instructions produce an identical final frame at either setting — the value changes pacing only |
| ROM written to a temp file | setup | `RAM(rom_path)` loads from a path. | — |
| `cpu.decode` wrapped to count instructions | — | Their `cycle()` drives the loop, so the adapter cannot otherwise count. Counting only. | **[tested]** counted total matches the frame rule |

## debugloop/chip8

| change | kind | why | evidence |
|---|---|---|---|
| No pygame at all; `ui.py` (curses) is never imported | — | Their emulator takes an injectable UI. | — |
| `DebugloopUI` mirrors their UI seam: an **unbounded** set of `(x, y)`, bounded only at frame capture | stub | Their `draw_sprite` neither wraps nor clips, and their collision check reads the same unbounded set. Imposing wrapping would change behaviour they did not write. | **[tested]** glyph matches the reference |
| `screen_redraw` is a no-op | stub | It only repaints curses. The set *is* the display. | — |
| `emu.time.sleep` neutralised | config | They sleep 1/300s per cycle to pace a live game. | **[tested]** identical frames with the real sleep restored |
| ROM written to a temp file | setup | `Chip8(filename, ui)` loads from a path. | — |

## IslayLaphroaig/CHIP-8

| change | kind | why | evidence |
|---|---|---|---|
| **No stubbing of any kind** | — | No GUI dependency. | — |
| `load_data("font_set", 0)` then the ROM at 512 | setup | Their `main.py` does exactly this. | **[tested]** glyph matches the reference |
| `update_timers()` once per frame | setup | Their `main.py` does it per frame. | **[tested]** the delay timer advances |

---

# Why each interpreter fails — their code, not the adapter

The headline observation rests on six interpreters failing the correctness suite, so each failure
has to be traceable to *their* source rather than to something the adapter did. Line numbers are
at the pinned commits. Four of six are traced; the remaining two are marked honestly as untraced.

All six draw exactly 230 lit pixels on the ibm-logo control, identical to the reference and to
each other — so the adapters run them correctly. What follows are defects in the interpreters.

### wyattferguson — `chip8/cpu.py:157-160`

```text
def _store_vx_result(self, value: int) -> None:
    self.v[CARRY_FLAG] = value >= 0
    self.v[self.x] = value % MAX_8BIT
```

Three defects in four lines. `MAX_8BIT` is 255, so `% MAX_8BIT` wraps at 255 rather than 256 and
a legitimate result of 255 becomes 0. `add_vx_vy` passes `total - MAX_8BIT`, so carry is flagged
when the total is ≥ 255 rather than > 255. And VF is written *before* VX, so when `x == 0xF` the
store clobbers the flag — exactly the "can vF be used as the vX input" case the flags test checks.

### robertolaru — `cpu.py:256-261`

```text
res = (self.v[vx] + self.v[vy]) & 0xff
self.v[vx] = res
if res > 0xff:
    self.v[0xf] = 1
```

`res` is masked to 8 bits on the line above, so `res > 0xff` can never be true. The carry branch
is dead code and VF is always 0.

### debugloop — `emu.py:112-114`

```text
result = self.v[...] + self.v[...]
self.v[0xf] = result & 0xf0000
self.v[...] = result & 0xffff
```

An 8-bit addition maxes at 510 (`0x1FE`), so `& 0xf0000` is always 0 and VF is never set. The
result is then masked to 16 bits rather than 8, leaving Vx untruncated.

### cwithmichael — `cpu.py:172-176`

The carry test itself is correct (`v[y] > 0xFF - v[x]`), but VF is assigned *before* the addition
is stored. When VF is the destination or an operand the sum overwrites the flag — the same
vF-as-operand case as wyattferguson, arrived at independently.

### islay — `src/chip8.py:99-129`

```text
def set_vx_to_vx_plus_vy(self):
    self.v[0xF] = 0
    total = self.v[self.x(self.opcode)] + self.v[self.y(self.opcode)]
```

The carry and borrow *logic* is right (`total > 255`, `difference < 0`). The ordering is not: VF
is written before the operands are read, so when VX or VY is VF the operand read returns the flag
just written rather than the register's value. That is worse than the usual vF-as-operand defect,
which corrupts only the flag; here it corrupts the arithmetic. Separately,
`set_vx_to_vx_shl_1` (line 129) assigns `self.v[x] << 1` with no `& 0xFF`, leaving VX above 255.

### rudzen — `cpu.py:128, 134`

```text
elif sub_op == 5:  # SUB Vx, Vy
    chip8.v[15] = 1 if chip8.v[vx] > chip8.v[vy] else 0
```

Borrow is computed with `>` where it needs `>=`. When VX == VY the subtraction does not borrow, so
VF should be 1; this sets 0. The same off-by-one repeats for SUBN at line 134. VF is also assigned
before VX in every branch of the `8XY_` group, so a VF destination clobbers the flag.

### robertolaru and cwithmichael, second defect — sprite rows spill onto the next scanline

`robertolaru/cpu.py:317` and `cwithmichael/cpu.py:243` compute the framebuffer position as a
single linear index:

```text
pos = (x + (y + h) * 64 + i) & 0x7ff          # robertolaru
idx = (vx + xline + ((vy + yline) * 64)) % GFX_SIZE   # cwithmichael
```

When `x + i` reaches 64 the index rolls into the **next row** instead of back to column 0 of the
same row, so part of a sprite row is drawn one scanline lower. Both arrived at the same shortcut
independently; it is a common one.

Verified causally: a one-row sprite of `0xFF` drawn at x=62, y=0 must occupy a single scanline.
Both place columns 62–63 on row 0 and the remaining six pixels on **row 1**. Every other
interpreter keeps the row intact — three wrap within the row, two clip at the edge, and both of
those are defensible readings of the quirk. Spilling onto the next row is not.

Found by ROM C, not by the reference suite: the only test ROM in that suite covering sprite edge
behaviour is the quirks ROM, which is timer-dependent and excluded here.

### All six traced

No interpreter's failure is now recorded as "the suite said so" without a cause in its own source.
