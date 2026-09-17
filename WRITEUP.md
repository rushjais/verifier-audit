# Is this grader fair?

**Draft — 2026-09-16. Not published.** Numbers reproduce from this repository; commands in §9.

> **TL;DR.** Built an instrument that measures whether a grader accepts correct work, returns the
> same verdict twice, and tests only what it told the candidate — not just whether it can be
> cheated. It produced four modest numbers and one negative result: the headline study, comparing
> five grading strategies on real third-party CHIP-8 interpreters, could not be run, for three
> reasons each measured rather than guessed. The most useful section is §7 — eleven times during
> construction a measurement here was confidently about something other than what it claimed.

**Authorship.** Built with Claude Code. I set the direction, made the scoping calls, reviewed the
output, and pushed back on it — including the two eligibility amendments and the decision not to
weaken the correctness bar a second time. The code and most of the prose were written by the
model under that direction. §7 records who introduced each defect.

---

## 1. Standing conclusion

**A verifier can be un-gameable and still be wrong, and the second failure is invisible in any
single run.** Robustness tooling exists. The other properties — does it accept correct work, does
it agree with itself, does it test only what the prompt made knowable — *are* checked today, but by
hand, per benchmark, once, by people who then move on. What does not exist is an automated
per-grader version that can be re-run as a grader changes.

Four numbers came out of this, all modest and all scoped in §3: a mutation catch rate below 1.0 on
2 of 5 EvalPlus tasks; a null result on hardening; a 1-in-6 honest-pass on an authored replication
task; and 1 of 7 CHIP-8 interpreters passing a reference suite.

---

## 2. What the instrument measures

    4a  honest_pass  = accepted / |{s : oracle(s) = 1}|      correct work the grader accepts
    4e  catch_rate   = rejected / |{m : oracle(m) = 0}|      broken work the grader rejects
    4b  flake_rate   = unstable / |{submissions × m runs}|   verdicts that change on rerun
    4b′ harness path   does the grader's own test exercise what the rollout exercises
    4c  unknowable     what the grader asserts that the prompt never made derivable

`4a` and `4e` are the same shape: sensitivity and specificity against the oracle. Either is
trivially maximised alone — accept everything, reject everything — so neither is reported without
the other. Every number carries the population it was computed over.

---

## 3. Results

### 3.1 On 2 of the 5 sparsest-coverage EvalPlus tasks, the base grader misses synthetic bugs

`catch_rate = rejected / |{m in mutants : oracle(m) = 0}|`. Mutants are **synthetic**: single-point
AST edits of the reference (comparison swaps, arithmetic swaps, boolean swaps, constant bumps),
then differentially filtered so behaviourally-equivalent ones are excluded and counted separately.
They are a proxy for real defects, not a sample of them.

| task | catchable mutants | caught | catch_rate | equivalent (excluded) | honest_pass | flake | shapes/20 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HumanEval/81 | 8 | 5 | **0.62** | 0 | 1.00 | 0.00 | 16 |
| HumanEval/105 | 8 | 8 | 1.00 | 0 | 1.00 | 0.00 | 19 |
| HumanEval/6 | 6 | 6 | 1.00 | 1 | 1.00 | 0.00 | 18 |
| HumanEval/75 | 4 | 3 | **0.75** | 4 | 1.00 | 0.00 | 20 |
| HumanEval/39 | 7 | 7 | 1.00 | 1 | 1.00 | 0.00 | 19 |

**The denominators are small — 8 and 4.** "0.75" is three mutants out of four. Read as counts, the
result is: *three missed mutants across five tasks*, on a capped sample of 8 mutants per task. That
is a demonstration that the check works and finds something, not a measurement of grader strength.

This **replicates the motivation for EvalPlus itself**, which exists because HumanEval's base tests
are too sparse to catch wrong code; it does not extend it. The contribution is that the number is
produced automatically, per grader, for **$0** — mutants need no model calls.

### 3.2 Null result: hardening cost nothing

`honest_pass` delta from grader to hardened grader was **0.00 on all five tasks** — zero
verified-correct solutions rejected. Recorded, not dropped. Credible only because diversity held:
16–20 structurally distinct solution shapes out of 20 per task, measured by AST fingerprint with
names erased. A null over a homogeneous population would mean nothing.

### 3.3 A differential grader rejected five of six spec-faithful implementations

`honest_pass = accepted / |{s in 6 proposed : oracle(s) = 1}| = 1/6 = 0.17`

A replication task: build a module from a spec, graded by structural comparison against a hidden
reference. The spec leaves four things undetermined and the reference picks one of each — a
record's type, the summary's type, which exception signals bad input, the average's precision.
Every rejection traces to one of those four.

**This is a pilot and the spec gap is authored by me.** It shows the instrument detects what it was
built to detect. It is not evidence about differential graders in the wild.

### 3.4 The hackathon project's headline result had a hole

This continues **Goodhart**, a two-day hackathon project by Advay Monga, rayan-arya and me, which
placed 9th of 71. The verifier core was Advay's and rayan's work; mine was the frontend. It sealed
harness tampering by rebuilding the test suite from the task — which sealed *file* tampering but
not in-process answer extraction:

```python
import test_cases; return dict(test_cases.CASES)[args]   # answers by module
sys._getframe(1).f_locals["expected"]                    # answers by stack frame
test_cases._eq = lambda a, b: True                       # neuter the comparison
```

**Verifying the zeroes are real.** A score of 0 can mean "blocked" or "nothing ran" — incident #4
in §7 is exactly that failure. These are blocked: `tests/test_isolation.py` asserts each exploit
scores **1** against a reconstruction of the old design, in the same sandbox, in the same run,
before asserting 0 against the fix; and `test_hardening_did_not_cost_the_gold_solution` asserts the
gold scores 1 under the fix. A sandbox that failed to start would fail all three.

### 3.5 One of seven CHIP-8 interpreters passes the reference suite

| interpreter | failures | cause, at the pinned commit |
| --- | --- | --- |
| craigthomas | **0** | — |
| wyattferguson | 8 | `cpu.py:157-160` — `% 255` not `% 256`; carry at ≥ 255; VF written before VX |
| robertolaru | 12 | `cpu.py:256-261` — `res` masked to 8 bits then tested `> 0xff`; dead branch |
| rudzen | 14 | `cpu.py:128,134` — borrow uses `>` where it needs `>=` |
| islay | 18 | `src/chip8.py:99-129` — VF written before operands are read; `SHL` unmasked |
| cwithmichael | 18 | `cpu.py:172-176` — VF assigned before the sum is stored |
| debugloop | 18 | `emu.py:112-114` — `& 0xf0000` on an 8-bit add is always 0 |

Population: seven Python CHIP-8 interpreters found by GitHub search, permissively licensed and
adaptable to a headless harness. **Not random, not cross-language, not a rate.** All seven produce
identical output on the quirk-free control, so the adapters run them correctly; every failure is
now traced to a line in their own source (`ADAPTERS.md`).

What this supports is narrow: **when choosing a reference implementation for differential grading,
correctness cannot be assumed from the fact that something is a working, published interpreter.**

---

## 4. The study that could not be run

The centrepiece was to reproduce GBA Eval's five grading strategies — exact match, pixel
proportion, thresholded, GMSD, SSIM — as a table of numbers, by measuring how each ranks
correct-but-different CHIP-8 interpreters. Three obstacles, each measured:

1. **Correct implementations are rare in this sample.** 1 of 7 (§3.5). A population of one supports
   neither `honest_pass` over a population nor rotating the reference.
2. **The only quirk-exercising ROM is timer-dependent.** `5-quirks.ch8` reads its delay timer in a
   frames-per-second detection loop to test the display-wait quirk. This population disagrees about
   timer semantics by construction. Confirmed three ways: source reading; timers-on vs timers-off
   comparison; and a frame sweep showing timer dependence by frame 20 while quirk differences do
   not appear until far later. Forcing the platform via `memory[0x1FF]` does not help.
3. **No timer-free *test ROM* tried exposes a quirk difference.** corax89's `test_opcode.ch8` is
   timer-free, MIT, settled by frame 60, and quirk-insensitive despite containing `8XY6`, `8XYE`,
   `FX55`, `FX65` and three logical ops; metteo's two are inert here. Nor do `craigthomas`'s own
   documented quirk flags change the display on any of them. **Games were not tried** — a real
   game that depends on a quirk would very likely show the difference, and that is untested.

**Predictions 1–9 are unrun**, standing pre-registered and unresolved rather than dropped. The
eligibility rule was amended twice, both before any metric existed, both recorded with reasoning —
including that Amendment 1 was made *after* the strict rule returned an unusable answer, by the
same party that would write the metrics.

---

## 5. Rejected hypotheses — do not re-test

1. **Hardening over-tightens EvalPlus graders.** No. Delta 0.00 across 5 tasks.
2. **`honest_pass` on stock EvalPlus is informative.** No — the oracle is a strict superset of the
   grader, so it is ~1.0 by construction.
3. **Agreement with my reference indicates correctness.** No; the ROM's own marks had to adjudicate.
4. **Raw mark counts adjudicate a test ROM.** No — the failure glyph also occurs inside the label
   text, producing a uniform false `err=8` for every interpreter including the reference.
5. **Forcing the quirks ROM's platform removes its timer dependence.** No.
6. **Third-party quirk flags substitute for a quirk-exercising ROM.** No.

## 6. Limitations

- §3.1 denominators are 4–8 mutants per task, capped; n=5 tasks. §3.3 is a pilot on an authored
  task. §3.5 is a convenience sample of seven.
- Timer semantics are **not** normalised across the CHIP-8 population and cannot be without
  rewriting those projects.
- `4c` ran only as a hand-verified pilot; `4b′` is an instrumentation helper plus a checklist
  demonstrated on two graders, not a generic checker.
- Games were never tried as quirk-exercising ROMs (§4.3).

---

## 7. Eleven measurements that were about the wrong thing

Assembled while building an instrument to detect exactly this. **Nine were introduced by the model
during this work** (marked ▲); #1 was in the original hackathon code, which all three of us wrote;
#2 is a property of git that nobody introduced and nobody noticed.

| # | claimed | true | how it surfaced |
| --- | --- | --- | --- |
| 1 | harness tampering categorically sealed | answers readable from the test module's namespace | reading another team's public writeup |
| 2 | the pre-commit gate was running | `core.hooksPath` is local config; a clone doesn't carry it | a commit succeeded that should have been blocked |
| 3 ▲ | `make check` passed | piped to `tail`, so the exit status was `tail`'s | **the lint error was printed and ignored**; found later by a bare `ruff check` |
| 4 ▲ | every exploit was sealed | `RLIMIT_AS` raised on macOS, so no sandboxed run started | a traceback, from tests written days earlier for another purpose |
| 5 ▲ | a working interpreter crashed | my `pygame.key` stub returned `{}` where a sequence was required | a `KeyError` traceback |
| 6 ▲ | timers were running | the adapter never called `decrement_timers()` | reading their `emulator.py` for an unrelated reason |
| 7 ▲ | frames were comparable | one adapter built them from 12 instructions, the rest from 15 | reading their `cycle()` |
| 8 ▲ | the tightened eligibility rule applied | fields added to the dataclass, table never updated — inert | test failures |
| 9 ▲ | the quirks ROM was excluded for needing input | hardcoded reason string; it is timer-dependent | reading the report's own output |
| 10 ▲ | a rounding variant passed the grader | no visible input produced a repeating average | reading the result table |
| 11 ▲ | a hardening test asserted something | `assert x == y or x != y` cannot fail | re-reading my own test |

**Correcting an earlier draft of this section:** it claimed none was caught by an error message.
That is false. #4, #5 and #8 surfaced as tracebacks or test failures, and #3 printed an error that
was displayed and ignored. The accurate claim is narrower: **none was caught by the thing it broke
failing at the moment it broke.** The tracebacks came from tests written for other purposes, days
later; the rest came from reading output that looked wrong.

That correction is itself the twelfth instance, and the reason the section is here.

---

## 8. What would make this a real study

1. **Author a quirk-exercising ROM, pre-registered before it is written.** This is the primary next
   step. A ROM is an **input**, not a member of the population: the population is the interpreters,
   and it stays third-party. Authoring an input is what GBA Eval does when it chooses which games
   to replay. The risk is tuning the input until a chosen strategy fails, and the mitigation is
   pre-registration — commit the ROM's exact design and the prediction *before* writing it, keep it
   trivially inspectable (draw a glyph at an x position computed via `8XY6`), and publish its
   source alongside its bytes.
2. **Try real games as quirk-exercising ROMs** (§4.3). Untried, plausibly sufficient, and entirely
   third-party — strictly better than authoring one if it works.
3. **Three or more fully-clean interpreters**, at roughly a dozen more adaptations.
4. Then Predictions 1–9, unchanged, against the five strategies.

## 9. Reproduce

```bash
uv sync
make check                                    # 155 tests, offline, no API key
python -m vaudit.tasks.chip8.fetch            # population + ROMs, pinned commits
python -m vaudit.audit.sweep --tasks 5        # prices the run; buys nothing without --confirm
```

§3.1 and §3.2 were produced in the predecessor repository before the clean-room rewrite; the
sweep command reproduces them here but regenerates the solution population, which costs ~$0.35.

## 10. External claims, for checking

Every claim in this document that rests on someone else's words, with its source. **Read and
verified by me:** 1–4, 6, 7. **Not independently verified — please check before publication:**
5 and 8.

| # | claim | source |
| --- | --- | --- |
| 1 | GBA Eval defines fairness as a perfect score being possible + ranking correlated with human judgement; five grading attempts | https://gbaeval.com/blog/grading-iteration |
| 2 | Mesen2 described as "one of the most accurate software GBA emulators available"; graded via SSIM / log-mel / test ROMs | https://gbaeval.com/ |
| 3 | Replication training; "writing effective and comprehensive tests remains a non-trivial task" | https://www.mechanize.work/blog/the-upcoming-gpt-3-moment-for-rl/ |
| 4 | A cross on the flags test means "you have an issue in your interpreter logic" | https://github.com/Timendus/chip8-test-suite — README, Flags test |
| 5 | SWE-bench Verified used human annotators to screen for over-specific tests and underspecified problems | https://openai.com/index/introducing-swe-bench-verified/ — **unverified** |
| 6 | TestBench-Forge reported a call-stack exploit against their own reward | https://www.aivalley.io/hackathons/hud-frontier-rsi-rl-environments-hackathon/projects — TestBench-Forge |
| 7 | corax89's test ROM, the basis Timendus adapted | https://github.com/corax89/chip8-test-rom |
| 8 | EvalPlus exists because HumanEval's base tests are too sparse | https://github.com/evalplus/evalplus — **unverified** |
