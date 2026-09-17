# Upstream issues — filed 2026-09-17

All four were filed after review. Each links to the issue as posted; the text below is what was
submitted, minus the suggested-fix blocks that were dropped before filing.

| repo | issue |
| --- | --- |
| `robertolaru/chip8py` | https://github.com/robertolaru/chip8py/issues/1 |
| `rudzen/Chip8Py` | https://github.com/rudzen/Chip8Py/issues/2 |
| `IslayLaphroaig/CHIP-8` | https://github.com/IslayLaphroaig/CHIP-8/issues/1 |
| `cwithmichael/chip8_py` | https://github.com/cwithmichael/chip8_py/issues/2 |

`wyattferguson/chip8-emulator` and `debugloop/chip8` have issues disabled and could not be
filed. Their defects are recorded in `ADAPTERS.md` and remain unreported upstream.

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

Reading the source is not enough to say a line *causes* a failure. Each claim below is confirmed
by a minimal ROM isolating one behaviour: it computes a value into `V0` and draws `V0` as a font
digit, so the rendered digit is the answer and no debugger access is needed.

| probe | correct | robertolaru | rudzen | islay | cwithmichael |
| --- | --- | --- | --- | --- | --- |
| carry: `V0=200, V1=100, 8014`, draw `VF` | `1` | **0** | 1 | 1 | 1 |
| borrow when equal: `V0=5, V1=5, 8015`, draw `VF` | `1` | 1 | **0** | 1 | 1 |
| `VF` as operand: `V0=5, VF=3, 80F4`, draw `V0` | `8` | 8 | 8 | **5** | **5** |
| `VF` as destination: `VF=200, V1=100, 8F14`, draw `VF` | `1` | **0** | **✗** | **✗** | **✗** |

`✗` means no font digit was drawn at all: `VF` held the sum (44) rather than the carry, so the
following `FX29` indexed outside the font table. The reference and `craigthomas` draw the correct
digit on all four probes, so the probes measure the interpreters and not the harness.

For `robertolaru` the single defect below explains both of its failures; the others have two
distinct symptoms from one root each.

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

`res` is masked to 8 bits on the first line, so `res > 0xff` is never true and `VF` is always set
to 0.

Reproduce with `4-flags.ch8` from the Timendus CHIP-8 test suite, which renders a cross for each
incorrect flag. Minimal check: `V0=200, V1=100, 8014` should leave `VF=1`; it leaves 0.

Found while testing several open-source CHIP-8 interpreters against the standard test suite.

---

## 2. `rudzen/Chip8Py`

**Title:** `8XY5` / `8XY7` set the borrow flag wrongly when the operands are equal

`cpu.py`:

```text
elif sub_op == 5:  # SUB Vx, Vy
    chip8.v[15] = 1 if chip8.v[vx] > chip8.v[vy] else 0
```

`VF` should be 1 when there is *no* borrow, i.e. when `Vx >= Vy`. With `>`, the equal case —
result 0, no borrow — sets 0 instead. `8XY7` at line 134 has the same comparison with the operands
reversed.

Separately, `VF` is assigned before `V[vx]` in every branch of the `8XY_` group, so an instruction
whose destination is `VF` ends up holding the result rather than the flag.

Reproduce with `4-flags.ch8` from the Timendus CHIP-8 test suite. Minimal checks: `V0=5, V1=5,
8015` should leave `VF=1`, and `VF=200, V1=100, 8F14` should leave `VF=1`.

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
not only the flag. When `VF` is the destination it ends up holding the result instead of the flag.
`set_vx_to_vx_minus_vy` and `set_vx_to_vy_minus_vx` share the ordering.

Also, `set_vx_to_vx_shl_1` assigns `self.v[x] << 1` with no `& 0xFF`, so `VX` can exceed 255.

Reproduce with `4-flags.ch8` from the Timendus CHIP-8 test suite, which checks the `VF`-as-operand
cases directly. Minimal check: `V0=5, VF=3, 80F4` should leave `V0=8`; it leaves 5.

Found while testing several open-source CHIP-8 interpreters against the standard test suite.

---

## 4. `cwithmichael/chip8_py`

**Title:** `8XY4` writes `VF` before the result

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
when `VF` is an operand the addition reads the value just written, and when it is the destination
the sum overwrites the flag. The subtract opcodes below share the ordering.

Reproduce with `4-flags.ch8` from the Timendus CHIP-8 test suite. Minimal check: `V0=5, VF=3,
80F4` should leave `V0=8`; it leaves 5.

Found while testing several open-source CHIP-8 interpreters against the standard test suite.
