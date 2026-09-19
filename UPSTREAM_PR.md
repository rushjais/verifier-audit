# Draft pull request, `wyattferguson/chip8-emulator`

**FILED 2026-09-18, https://github.com/wyattferguson/chip8-emulator/pull/9** (open, mergeable, +6/−3 in one file).

This repo has issues disabled, so a pull request was the only channel; it is actively maintained
(last push 2026-08-01). Before filing, the defect was confirmed present at their **current HEAD**
(`d62e55d`), not only at the commit this project pinned, and the fix was re-verified against that
HEAD: `wyattferguson` goes from 8 failures-against-peers to 0 on `4-flags.ch8`, 47 of 47 marks,
and no other interpreter's score moves.

Two of the draft's three open questions were carried into the PR body rather than decided
unilaterally, the `bool`-vs-`int` store was left alone as out of scope for an ordering fix, and
no test was included since the repo has no suite, both offered to the author. The third, whether
to send PRs to the four repos with open unanswered issues, is still undecided and is the user's
call.

---

## Title

```
Set VF after the destination register in 8XY4/5/7 and 8XY6/E
```

## Body

```markdown
`chip8/cpu.py` writes `VF` before it writes `V[x]`. When `x` is `0xF` the second write
overwrites the flag with the arithmetic result, so any instruction that targets `VF` loses its
carry or borrow.

```python
def _store_vx_result(self, value: int) -> None:
    self.v[CARRY_FLAG] = value >= 0   # flag written first
    self.v[self.x] = value % MAX_8BIT # ...then clobbered when self.x == 0xF
```

`shr_vx` and `shl_vx` have the same ordering.

**Repro.** `8F14` (ADD VF, V1) with `VF = 200` and `V1 = 100`:

`VF` should hold `1`, the carry. It holds `44`, the low byte of 200 + 100.

On `Timendus/chip8-test-suite`, `4-flags.ch8` reports 8 failures, all of them the "vF as the
destination" cases.

**Fix.** Compute the flag, store the result, then store the flag. Three call sites, no change to
any value, only to the order they are written in.

**After this change** `4-flags.ch8` reports 0 failures (47 of 47 marks pass, up from 39).
Arithmetic is unaffected: `MAX_8BIT` is 256, so the existing wrap and the `value >= 0` carry
test were already correct. I checked `ADD 200+100 → 44/VF=1`, `ADD 100+50 → 150/VF=0`,
`SUB 5-10 → 251/VF=0`, `SUB 10-5 → 5/VF=1` before and after, all unchanged.

I found this while using several open-source CHIP-8 interpreters as a test population for an
unrelated project.
```

## Diff

```diff
--- a/chip8/cpu.py
+++ b/chip8/cpu.py
@@
     def _store_vx_result(self, value: int) -> None:
         """Store value in Vx and update VF."""
-        self.v[CARRY_FLAG] = value >= 0
-        self.v[self.x] = value % MAX_8BIT
+        carry = value >= 0
+        self.v[self.x] = value % MAX_8BIT
+        self.v[CARRY_FLAG] = carry

     def shr_vx(self) -> None:
         """Set Vx = Vx SHR 1."""
-        self.v[CARRY_FLAG] = self.v[self.x] & 0x1
-        self.v[self.x] >>= 1
+        carry = self.v[self.x] & 0x1
+        self.v[self.x] >>= 1
+        self.v[CARRY_FLAG] = carry

     def shl_vx(self) -> None:
         """Set Vx = Vx SHL 1."""
-        self.v[CARRY_FLAG] = (self.v[self.x] & 0x80) >> 7
-        self.v[self.x] = (self.v[self.x] << 1) % MAX_8BIT
+        carry = (self.v[self.x] & 0x80) >> 7
+        self.v[self.x] = (self.v[self.x] << 1) % MAX_8BIT
+        self.v[CARRY_FLAG] = carry
```

## Measured result

Patched a copy at the pinned commit, re-ran `4-flags.ch8` for 60 frames, and re-scored the whole
population. Only `wyattferguson` changed:

| interpreter | before | after |
| --- | ---: | ---: |
| craigthomas | 0 | 0 |
| **wyattferguson** | **8** | **0** |
| robertolaru | 10 | 10 |
| rudzen | 14 | 14 |
| cwithmichael | 15 | 15 |
| debugloop | 15 | 15 |
| islay | 16 | 16 |

Counts are failures *against peers*, tests an interpreter fails that another one passes. After
the change `wyattferguson` joins `craigthomas` as the only members with none.

## Before submitting, open questions for the author

1. **Style.** `self.v[CARRY_FLAG] = value >= 0` stores a `bool`, not an `int`. The diff preserves
   that rather than changing it, to keep the change to ordering alone. Worth deciding whether to
   fix separately.
2. **Tests.** The repo has none for this. Offering one alongside the fix would make the PR more
   useful, but adds surface the author may not want.
3. **Courtesy.** The four repos with issues enabled have open reports from us and no replies yet.
   Sending PRs there too would be reasonable, but those authors have not had a chance to fix
   their own code; this repo is different only because a PR is the sole available channel.
