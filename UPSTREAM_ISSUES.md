# Upstream issue drafts — for review, not filed

**Nothing here has been posted.** Four drafts, one per eligible repository.

## Eligibility, checked 2026-09-17

| repo | archived | issues enabled | existing issue for this | eligible |
| --- | --- | --- | --- | --- |
| `robertolaru/chip8py` | no | yes | none (0 issues total) | yes |
| `rudzen/Chip8Py` | no | yes | none (1 issue, unrelated) | yes |
| `IslayLaphroaig/CHIP-8` | no | yes | none (0 issues total) | yes |
| `cwithmichael/chip8_py` | no | yes | none (1 issue, unrelated) | yes |
| `wyattferguson/chip8-emulator` | no | **disabled** | — | no — cannot file |
| `debugloop/chip8` | no | **disabled** | — | no — cannot file |

Every bug below was confirmed present at the repository's current HEAD, not only at the commit
this project pinned.

## How each cause was verified

Reading the source is not enough to say a line *causes* a failure. Each was confirmed with a
minimal ROM that isolates one behaviour, computes a value into `V0`, and draws `V0` as a font
digit — so the rendered digit is the answer and no debugger access is needed. A correct
interpreter draws the expected digit; each of these draws a different one.

| repo | probe | correct | observed |
| --- | --- | --- | --- |
| robertolaru | `V0=200, V1=100, 8014`, then draw `VF` | `1` | `0` |
| rudzen | `V0=5, V1=5, 8015`, then draw `VF` | `1` | `0` |
| islay | `V0=5, VF=3, 80F4`, then draw `V0` | `8` | `5` |
| cwithmichael | `V0=5, VF=3, 80F4`, then draw `V0` | `8` | `5` |

The reference and the three unaffected interpreters draw the correct digit on every probe, so the
probes are not measuring the harness.

---

## 1. `robertolaru/chip8py`

**Title:** `8XY4` never sets the carry flag

`cpu.py`, `add_reg`:

```text
res = (self.v[vx] + self.v[vy]) & 0xff
self.v[vx] = res
if res > 0xff:
    self.v[0xf] = 1
```

`res` is masked to 8 bits on the first line, so `res > 0xff` is never true and `VF` is always 0.

Reproduce: `4-flags.ch8` from the Timendus CHIP-8 test suite renders a cross for each incorrect
flag. Minimal check: `V0=200, V1=100, 8014` should leave `VF=1`; it leaves 0.

Suggested fix — keep the unmasked total for the test, and write `VF` last so that `8XF4`, where
the destination is `VF` itself, keeps the flag rather than the sum:

```text
total = self.v[vx] + self.v[vy]
self.v[vx] = total & 0xff
self.v[0xf] = 1 if total > 0xff else 0
```

Found while testing several open-source CHIP-8 interpreters against the standard test suite.

---

## 2. `rudzen/Chip8Py`

**Title:** `8XY5` / `8XY7` set the borrow flag wrongly when the operands are equal

`cpu.py`:

```text
elif sub_op == 5:  # SUB Vx, Vy
    chip8.v[15] = 1 if chip8.v[vx] > chip8.v[vy] else 0
```

`VF` should be 1 when there is *no* borrow, i.e. `Vx >= Vy`. With `>`, the equal case — result 0,
no borrow — sets 0 instead of 1. The same applies to `8XY7` at line 134 with the operands
reversed.

Reproduce: `4-flags.ch8` from the Timendus CHIP-8 test suite. Minimal check: `V0=5, V1=5, 8015`
should leave `VF=1`; it leaves 0.

Suggested fix: `>=` in both places. Separately, `VF` is assigned before `V[vx]` in every branch of
the `8XY_` group, so an instruction whose destination is `VF` overwrites the flag with the result.

Found while testing several open-source CHIP-8 interpreters against the standard test suite.

---

## 3. `IslayLaphroaig/CHIP-8`

**Title:** Arithmetic opcodes write `VF` before reading their operands

`src/chip8.py`:

```text
def set_vx_to_vx_plus_vy(self):
    self.v[0xF] = 0
    total = self.v[self.x(self.opcode)] + self.v[self.y(self.opcode)]
```

`VF` is written before the operands are read, so when `VX` or `VY` *is* `VF` the operand read
returns the flag just written rather than the register's value — the arithmetic result is wrong,
not just the flag. `set_vx_to_vx_minus_vy` and `set_vx_to_vy_minus_vx` share the ordering.

Reproduce: `4-flags.ch8` from the Timendus CHIP-8 test suite checks the `VF`-as-operand cases
directly. Minimal check: `V0=5, VF=3, 80F4` should leave `V0=8`; it leaves 5.

Suggested fix — compute into a local, write `VF` last:

```text
total = self.v[self.x(self.opcode)] + self.v[self.y(self.opcode)]
self.v[self.x(self.opcode)] = total & 0xFF
self.v[0xF] = 1 if total > 0xFF else 0
```

Also `set_vx_to_vx_shl_1` assigns `self.v[x] << 1` with no `& 0xFF`, so `VX` can exceed 255.

Found while testing several open-source CHIP-8 interpreters against the standard test suite.

---

## 4. `cwithmichael/chip8_py`

**Title:** `8XY4` writes `VF` before the result, losing the flag when `VF` is the destination

`cpu.py`:

```text
elif op == 4:
    if self.register[y] > (0xFF - self.register[x]):
        self.register[0xF] = 1
    else:
        self.register[0xF] = 0
    self.register[x] = (self.register[x] + self.register[y]) & 0xFF
```

The carry test itself is correct; the ordering is not. `VF` is assigned before `register[x]`, so
when the destination is `VF` the sum immediately overwrites the flag — and when `VF` is an
operand, the addition reads the value just written. The subtract opcodes below share the ordering.

Reproduce: `4-flags.ch8` from the Timendus CHIP-8 test suite. Minimal check: `V0=5, VF=3, 80F4`
should leave `V0=8`; it leaves 5.

Suggested fix:

```text
total = self.register[x] + self.register[y]
self.register[x] = total & 0xFF
self.register[0xF] = 1 if total > 0xFF else 0
```

Found while testing several open-source CHIP-8 interpreters against the standard test suite.
