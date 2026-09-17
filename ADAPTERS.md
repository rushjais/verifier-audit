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
