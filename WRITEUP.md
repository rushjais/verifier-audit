# Is this grader fair?

**Draft — 2026-09-16. Not published.** Numbers reproduce from this repository; commands in §9.

> **TL;DR.** Built an instrument that measures whether a grader accepts correct work, returns the
> same verdict twice, and tests only what it told the candidate — not just whether it can be
> cheated. It produced four modest numbers and one negative result: the headline study, comparing
> five grading strategies on real third-party CHIP-8 interpreters, could not be run, for three
> reasons each measured rather than guessed. The most useful section is §7 — fifteen times during
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
hand, per benchmark, once, by people who then move on.

The clearest precedent is **SWE-bench Verified**, and it is worth stating how exactly it matches.
OpenAI "launched a human annotation campaign with professional software developers to screen each
sample of the SWE-bench test set for appropriately scoped unit tests and well-specified issue
descriptions", working with **93 developers** over **1,699 samples** to produce a verified set of
**500**. Their two annotation criteria were:

> Whether we consider the issue description to be underspecified and hence unfair to be testing on.
>
> Whether the FAIL_TO_PASS unit tests filter out valid solutions.

Those are `4c` and `4a`. The problem is understood and the criteria are settled; what is missing
is a version that does not cost 93 people and cannot be re-run when a grader changes. That is the
gap this instrument aims at, and the honest framing of its contribution.

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
| HumanEval/81 | 8 | 5 | **0.62** | 0 | 1.00 (19 verified) | 0.00 | 16 |
| HumanEval/105 | 8 | 8 | 1.00 | 0 | 1.00 (20 verified) | 0.00 | 20 |
| HumanEval/6 | 6 | 6 | 1.00 | 1 | 1.00 (16 verified) | 0.00 | 19 |
| HumanEval/75 | 4 | 3 | **0.75** | 4 | 1.00 (18 verified) | 0.00 | 20 |
| HumanEval/39 | 7 | 7 | 1.00 | 1 | 1.00 (18 verified) | 0.00 | 19 |

**Provenance.** Generated 2026-09-17 in this repository. 100 solutions across 5 tasks, spread over
`claude-sonnet-5` (35), `claude-haiku-4-5` (35) and `claude-opus-5` (30), one style directive per
index. 31,603 input / 26,063 output tokens; actual spend ≈ $0.32 against a $0.35 estimate and a
$2.00 cap. **There is no seed.** The Anthropic API exposes no sampling seed, so the run is not
replayable; instead every solution is committed under `data/solutions/`, with its model, directive
and timestamp, so the table above reproduces offline with no API calls. Reproducibility here comes
from keeping the population, not from replaying the sampler.

**Differences from the predecessor-repository run.** Reported as they came out; nothing was rerun
to match.

| column | predecessor | this repo | note |
| --- | --- | --- | --- |
| catch_rate | 0.62, 1.00, 1.00, 0.75, 1.00 | **identical** | mutants are deterministic AST surgery — no model involved, so this was expected and it held |
| honest_pass | 1.00 × 5 | 1.00 × 5 | unchanged |
| flake_rate | 0.00 × 5 | 0.00 × 5 | unchanged |
| distinct shapes | 16, 19, 18, 20, 19 | 16, **20**, **19**, 20, 19 | two tasks gained one distinct shape |
| verified (of 20) | 19, 20, 17, 19, 18 | 19, 20, **16**, **18**, 18 | two tasks had one more solution fail the oracle |

The population-dependent columns moved by one in four places; the measured columns did not move at
all. §3.2's number is **not** in this comparison because it cannot be produced here at all — see
that section.

**The denominators are small — 8 and 4.** "0.75" is three mutants out of four. Read as counts, the
result is: *three missed mutants across five tasks*, on a capped sample of 8 mutants per task. That
is a demonstration that the check works and finds something, not a measurement of grader strength.

This **replicates the motivation for EvalPlus itself** and does not extend it. EvalPlus exists
because "test-cases can be limited in both quantity and quality for fully assessing the functional
correctness of the generated code"; it adds **80×** more tests than original HumanEval and reports
that doing so reduces "the pass@k by up-to 19.3-28.9%". Measured against that, three missed
mutants is a small echo of a known and much larger effect. The contribution is not the finding but
the mechanism: produced automatically, per grader, for **$0**, because mutants need no model calls.

### 3.2 Null result: hardening cost nothing — *not reproducible in this repository*

`honest_pass` delta from grader to hardened grader was **0.00 on all five tasks** — zero
verified-correct solutions rejected. Recorded, not dropped. Credible only because diversity held:
16–20 structurally distinct solution shapes out of 20 per task, measured by AST fingerprint with
names erased. A null over a homogeneous population would mean nothing.

**This is the one result here with no reproduce path.** Its artifact is archived at
`data/predecessor/m1a_sweep.json` — produced by code that is not in this repository — so the claim
rests on a file rather than only a sentence. The hardening track was deliberately
dropped in the clean-room rewrite — its patch template was my former teammates' code, and the
result was null — so the sweep that ships with this repository has no hardened column and cannot
produce this number. It stands as a result from the predecessor repository only. Re-adding a
hardening step of my own would make it reproducible and would also make it close to tautological:
hardening with extra cases derived from the reference cannot reject a correct solution, so the
null would be built into the construction rather than measured.

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

```text
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

## 7. Fifteen measurements that were about the wrong thing

Assembled while building an instrument to detect exactly this. **Thirteen were introduced by the
model during this work**; #1 was in the original hackathon code, which all three of us wrote; #2
is a property of git that nobody introduced and nobody noticed. The full list is Appendix A; what
matters is that they fall into four patterns, and the patterns are the finding.

### A. The check was not running (#2, #3, #4, #8, #12)

The most common failure, and the most dangerous, because an inert check is indistinguishable from
a passing one. `core.hooksPath` is local git config, so a clone has the hook files and no hook.
`make check | tail` reports `tail`'s exit status, so a failing gate reads as success. `RLIMIT_AS`
raised on macOS before any candidate ran, so every exploit scored 0 and every exploit looked
sealed. Fields were added to a dataclass and the table never updated, so a tightened eligibility
rule did nothing. `ruff check` was run and reported success while `make check` — a superset — was
failing.

**What distinguishes these: the system was quieter than before, not louder.** Nothing errored.
A sealed exploit, a green gate and a passing suite all look like progress.

### B. The claim was wider than the thing verified (#1, #11, #14, #15)

"Harness tampering categorically sealed" rested on a test covering file tampering only. A
hardening test asserted `x == y or x != y`, which cannot fail. "155 tests" was 111 passed and 14
skipped in the order the document gave. "The sweep reproduces §3.1 and §3.2" was true of one and
false of the other.

**Each was true of something narrower than its sentence.** None required a bug to produce — only
a summary written a little ahead of the evidence.

### C. My scaffolding was mistaken for their behaviour (#5, #6, #7, #13)

A `pygame.key` stub returning `{}` where a sequence was required made a working interpreter throw,
which read as "this implementation crashes on the quirks ROM" and nearly removed it from the
population. An adapter never called `decrement_timers()`, so timers silently never advanced. One
adapter built frames from 12 instructions while the rest used 15. `ruff format` rewrote quoted
third-party source — `0xff` → `0xFF` — inside evidence cited against those projects.

**This is the category the whole study is about**, arrived at from the inside: a misconfigured
subject and a defective one are indistinguishable from the outside, and the harness is the thing
most likely to be misconfigured.

### D. The fixture could not show what it was built to show (#9, #10)

A report hardcoded "needs live input" as the exclusion reason for every excluded ROM, so a
timer-dependent exclusion printed a confident wrong explanation. A `rounded_average` variant
passed the grader because no visible input produced a repeating average — the fixture could not
express the difference it existed to demonstrate.

---

**Correcting an earlier draft of this section:** it claimed none was caught by an error message.
That is false. #4, #5 and #8 surfaced as tracebacks or test failures, and #3 printed an error that
was displayed and ignored. The accurate claim is narrower: **none was caught by the thing it broke
failing at the moment it broke.** The tracebacks came from tests written for other purposes, days
later; the rest came from reading output that looked wrong.

That correction is itself the sixteenth instance, and the reason the section is here.

#12, #13, #14 and #15 were all found in one sitting, by running the documented commands from a
clean clone and by checking what the shipped code measures before running it. Four of fifteen came
from an hour of not trusting the documentation — which is the cheapest audit in this document and
the one with the highest yield.

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
python -m vaudit.tasks.chip8.fetch    # population + ROMs at pinned commits (network, no API key)
make check                            # 155 tests, offline, no API key
python -m vaudit.audit.sweep --tasks 5  # prices the run; buys nothing without --confirm
git config core.hooksPath .githooks   # optional: activate the pre-commit gate (incident #2)
```

**Order matters, and an earlier draft had it wrong.** Run `make check` before fetching and you get
**111 passed, 14 skipped** — the adapter tests skip cleanly when the population is absent, by
design, so the suite can never go green while silently claiming a study that did not run. Only
after fetching is it 155. The draft listed the steps the other way round and claimed 155 for the
first one.

**Verified from a clean clone on 2026-09-16**, which is how #12 and #13 were found: `make check`
was failing on the format step while `ruff check` alone reported success. Steps 1, 2 and 3 now
pass from a fresh clone with no API key and no pre-existing `.population`. Step 4 was run as a
dry run only; it prints the estimate and buys nothing.

Three caveats. §3.2 has no reproduce path in this repository at all (see that section);
`.githooks` is not active in a fresh clone — `git config core.hooksPath .githooks`
is required, and that is incident #2. And §3.1/§3.2 were produced in the predecessor repository
before the clean-room rewrite. §3.1 has since been regenerated **in this repository**
(2026-09-17) and its population is committed under `data/solutions/`, so it now reproduces with no
API calls. §3.2 remains predecessor-only.

## 10. External claims, for checking

Every claim in this document that rests on someone else's words, with its source. **All eight have
now been read at source.** 5 and 8 were checked after an earlier draft flagged them as unverified;
both hold, and both turned out stronger than the draft claimed.

| # | claim | source |
| --- | --- | --- |
| 1 | GBA Eval defines fairness as a perfect score being possible + ranking correlated with human judgement; five grading attempts | https://gbaeval.com/blog/grading-iteration |
| 2 | Mesen2 described as "one of the most accurate software GBA emulators available"; graded via SSIM / log-mel / test ROMs | https://gbaeval.com/ |
| 3 | Replication training; "writing effective and comprehensive tests remains a non-trivial task" | https://www.mechanize.work/blog/the-upcoming-gpt-3-moment-for-rl/ |
| 4 | A cross on the flags test means "you have an issue in your interpreter logic" | https://github.com/Timendus/chip8-test-suite — README, Flags test |
| 5 | **Verified, and stronger than stated.** 93 developers, 1,699 samples annotated, 500 verified. Criteria quoted verbatim in §1 and are exactly `4a` and `4c`. Their worked example is a test requiring an exact deprecation message the agent could not have known. | https://openai.com/index/introducing-swe-bench-verified/ |
| 6 | TestBench-Forge reported a call-stack exploit against their own reward | https://www.aivalley.io/hackathons/hud-frontier-rsi-rl-environments-hackathon/projects — TestBench-Forge |
| 7 | corax89's test ROM, the basis Timendus adapted | https://github.com/corax89/chip8-test-rom |
| 8 | **Verified.** "test-cases can be limited in both quantity and quality"; 80× more tests than original HumanEval; "reducing the pass@k by up-to 19.3-28.9%". Paper: *Is Your Code Generated by ChatGPT Really Correct?*, arXiv:2305.01210 | https://arxiv.org/abs/2305.01210 and https://github.com/evalplus/evalplus |

---

## Appendix A — the full list

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
| 12 ▲ | "all checks passed" | `ruff check` is lint only; `make check` also runs `ruff format --check`, which was failing | running the documented reproduce command from a clean clone |
| 13 ▲ | quoted third-party source was verbatim | `ruff format` rewrote the quotes (`0xff` → `0xFF`) in evidence cited against those projects | reading the diff the formatter produced |
| 14 ▲ | "`make check` — 155 tests" | in the documented order it is 111 passed, 14 skipped; the population has to be fetched first | running the steps as written, in the order written |
| 15 ▲ | "the sweep command reproduces §3.1 and §3.2 here" | true of §3.1, false of §3.2 — the clean-room rewrite dropped the hardening track, so this repo cannot produce that number at all | checking what the shipped sweep actually measures before running it |

#12, #13 and #14 were found by running §9's commands from a clean clone, which is why that is now part
of the procedure rather than an assumption. #13 is the sharpest of the set: a tool whose job is
maintaining quality silently modified the evidence, in a document arguing that measurements are
confidently about the wrong thing. Quoted source is now fenced as `text` so no formatter can
touch it.
