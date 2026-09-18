# Seventeen measurements that were about the wrong thing

**Last updated 2026-09-17.** Numbers reproduce from this repository; commands in §9.

> **TL;DR.** I set out to build an instrument that detects when a grader is unfair rather than
> merely gameable. The instrument works, and everything it measured turned out to be a replication
> of established results — the literature search in `LITERATURE.md` is unsparing about that. What
> the project produced that is not a replication is **a first-person record of seventeen
> occasions, inside one small project, where a measurement was confidently about something other
> than what it claimed**. Fifteen were introduced by the model doing the work. None was caught by
> the thing it broke failing at the moment it broke. They fall into four patterns, and each
> pattern has a direct analogue in building RL graders — which is the argument this document is
> actually making.

**Authorship.** Built with Claude Code. I set the direction, made the scoping calls, reviewed the
output, and pushed back on it — including the eligibility amendments, the decision not to weaken
the correctness bar, and the literature search that cost the project its novelty claims. The code
and most of the prose were written by the model under that direction. §2 records who introduced
each defect.

---

## 1. Why this is the finding

The project was an instrument for catching graders that are confidently wrong — that reject
correct work, disagree with themselves, or test what the prompt never made knowable. While
building it, the project committed that error seventeen times.

That is not irony for its own sake. The failures were **recorded as they happened, with their
causes traced, by someone who was specifically looking for that class of failure and still missed
every one at the moment it occurred.** Retrospective bug lists do not have that property; they
are assembled by people who already know the answer.

Four things make the record worth more than the results it accompanies:

1. **Every incident has a traced cause**, not a symptom — a source line where there is one, and
   for #2, #14, #16 and #17 a cause that is not a line at all. §2 and Appendix A give them.
2. **None was caught by the thing it broke failing at the moment it broke.** Three did surface as
   tracebacks or test failures, but from tests written days earlier for unrelated purposes.
3. **Each pattern maps onto a way real graders fail.** Pattern A is the acceptance test that never
   runs in production. Pattern C is harness misconfiguration read as a model's failure, which
   makes a fair task look unfair and an unfair one look fine. Pattern B is a rate reported over
   the wrong population.
4. **The project's own checks caught a minority of them.** Appendix A's surfacing column: tests
   and tracebacks **3** (#4, #5, #8), running or verifying a documented command **4** (#3, #12,
   #14, #17), reading code or output **8**, the repository's owner **1**, an unexpected state
   **1**. Reading beat testing better than two to one — though half of that reading was of *code*,
   not output.

The results that produced these incidents are in §4, labelled as the replications they are.

---

## 2. The seventeen

Assembled while building an instrument for the same class of failure in graders. **Fifteen were
introduced by the model during this work**; #1 was in the original hackathon code, which three of
us wrote; #2 is a property of git that nobody introduced and nobody noticed. The full list with
causes is Appendix A.

### A. The check was not running (#2, #3, #4, #8, #12, #17), and one that was never broken (#16)

The most common of the four — seven of seventeen — and an inert check is indistinguishable from
a passing one. `core.hooksPath` is local git config, so a clone has the hook files and no hook;
and in this repository there were no hook files either, so the command §9 gave for activating the
gate pointed at a directory that did not exist, set the config anyway, and exited 0.
`make check | tail` reports `tail`'s exit status, so a failing gate reads as success. `RLIMIT_AS`
raised on macOS before any candidate ran, so every exploit scored 0 and every exploit looked
sealed. Fields were added to a dataclass and the table never updated, so a tightened eligibility
rule did nothing. `ruff check` was run and reported success while `make check` — a superset — was
failing.

#16 belongs to this pattern from the outside and to a worse one from the inside. I observed a
state I did not expect, wrote "cause unestablished" — and then acted on it anyway, reverting a
deliberate decision by the repository's owner and filing it as a defect. **Recording that the
cause was unknown did not stop me treating it as known.** The honest lesson is not about stale
reads: an unexpected state is a question for whoever owns the system, not a fault to be corrected
by whoever noticed it.

**What distinguishes these: the system was quieter than before, not louder.** Nothing errored.
A sealed exploit, a green gate and a passing suite all look like progress.

### B. The claim was wider than the thing verified (#1, #11, #14, #15)

"Harness tampering categorically sealed" rested on a test covering file tampering only. A
hardening test asserted `x == y or x != y`, which cannot fail. "155 tests" was 111 passed and 14
skipped in the order the document gave. "The sweep reproduces §4.1 and §4.2" was true of one and
false of the other.

**Each was true of something narrower than its sentence.** None required a bug to produce — only
a summary written a little ahead of the evidence.

### C. My scaffolding was mistaken for their behaviour (#5, #6, #7, #13)

A `pygame.key` stub returning `{}` where a sequence was required made a working interpreter throw,
which read as "this implementation crashes on the quirks ROM" and nearly removed it from the
population. An adapter never called `decrement_timers()`, so timers silently never advanced. One
adapter built frames from 12 instructions while the rest used 15. `ruff format` rewrote quoted
third-party source — `0xff` → `0xFF` — inside evidence cited against those projects.

**This is the category §4.5 and §4.6 are about**, arrived at from the inside: a misconfigured
subject and a defective one are indistinguishable from the outside, and in all four of these the
misconfiguration was mine, not theirs.

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

That correction is itself another instance — unnumbered, because it is a claim about the list
rather than an entry in it — and the reason the section is here.

#12, #13, #14 and #15 were all found in one sitting, by running the documented commands from a
clean clone and by checking what the shipped code measures before running it. Four of seventeen
came from an hour of not trusting the documentation — the highest-yield hour in the project. #17
arrived the same way and later: checking whether the gate was on, immediately before a commit
that would have relied on it.

---

## 3. The instrument

    4a  honest_pass  = accepted / |{s : oracle(s) = 1}|      correct work the grader accepts
    4e  catch_rate   = rejected / |{m : oracle(m) = 0}|      broken work the grader rejects
    4b  flake_rate   = unstable / |{submissions × m runs}|   verdicts that change on rerun
    4b′ harness path   does the grader's own test exercise what the rollout exercises
    4c  unknowable     what the grader asserts that the prompt never made derivable

`4a` and `4e` are sensitivity and specificity against the oracle. Either is trivially maximised
alone — accept everything, reject everything — so neither is reported without the other. Every
number carries the population it was computed over.

**None of it is novel, and `LITERATURE.md` is the accounting.** `catch_rate` is the **mutation
score** (1977; 390+ publications catalogued by 2009) and its equivalent-mutant filter is a known
NP-complete problem. `honest_pass` is measured in the autograding literature, which reports
**56–64% false-negative rates** and names the mechanism §4.3 demonstrates. `4c`'s two questions
are verbatim the criteria OpenAI used for SWE-bench Verified with 93 annotators. SSIM's
sensitivity to translation — the basis of §4.6 — is a documented drawback with a purpose-built
fix, CW-SSIM (Wang & Simoncelli, 2005).

What has no prior art found for it is the **automated, per-grader combination**: one command
reporting fairness beside robustness for a specific grader, repeatably, as it changes. That search
was not exhaustive and `LITERATURE.md` says where it was thin.

---

## 4. What it measured

Replications, except where noted. Each is scoped to what its sample supports.

### 4.1 On 2 of the 5 sparsest-coverage EvalPlus tasks, the base grader misses synthetic bugs

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
all. §4.2's number is **not** in this comparison because it cannot be produced here at all — see
that section.

**The denominators are small — 8 and 4.** "0.75" is three mutants out of four. Read as counts, the
result is: *four missed mutants out of 33 catchable, across five tasks* — three on HumanEval/81
and one on HumanEval/75 — on a capped sample of at most 8 mutants per task. That is a
demonstration that the check works and finds something, not a measurement of grader strength.

This is the **mutation score** from mutation testing (1977), applied to a grader instead of a
test suite; the filter for behaviourally-identical mutants is the known equivalent-mutant problem.
It also **replicates the motivation for EvalPlus itself** and does not extend it. EvalPlus exists
because "test-cases can be limited in both quantity and quality for fully assessing the functional
correctness of the generated code"; it adds **80×** more tests than original HumanEval and reports
that doing so reduces "the pass@k by up-to 19.3-28.9%". Measured against that, four missed
mutants is a small echo of a known and much larger effect. **The automation is not a contribution
either** — mutation-testing tools have produced this number automatically for test suites since
the 1980s, and `LITERATURE.md` says so. What §3 claims is narrower: the same number reported
*beside* `honest_pass` and `flake_rate` for one specific grader, repeatably, as it changes.
Mutants do at least cost nothing to generate, since they need no model calls.

### 4.2 Null result: hardening cost nothing — *not reproducible in this repository*

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

### 4.3 A differential grader rejected five of six spec-faithful implementations

`honest_pass = accepted / |{s in 6 proposed : oracle(s) = 1}| = 1/6 = 0.17`

A replication task: build a module from a spec, graded by structural comparison against a hidden
reference. The spec leaves four things undetermined and the reference picks one of each — a
record's type, the summary's type, which exception signals bad input, the average's precision.
Every rejection traces to one of those four.

**This is a pilot and the spec gap is authored by me.** It shows the instrument detects what it was
built to detect. It is not evidence about differential graders in the wild.

### 4.4 The hackathon project's headline result had a hole

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
in §2 is exactly that failure. These are blocked: `tests/test_isolation.py` asserts each exploit
scores **1** against a reconstruction of the old design, in the same sandbox, in the same run,
before asserting 0 against the fix; and `test_hardening_did_not_cost_the_gold_solution` asserts the
gold scores 1 under the fix. A sandbox that failed to start would fail all three.

### 4.5 One of seven CHIP-8 interpreters fails nothing its peers pass

| interpreter | failures vs peers | cause, at the pinned commit |
| --- | --- | --- |
| craigthomas | **0** | — |
| wyattferguson | 8 | `cpu.py:157-160` — `% 255` not `% 256`; carry at ≥ 255; VF written before VX |
| robertolaru | 12 | `cpu.py:256-261` — `res` masked to 8 bits then tested `> 0xff`; dead branch |
| rudzen | 14 | `cpu.py:128,134` — borrow uses `>` where it needs `>=` |
| islay | 18 | `src/chip8.py:99-129` — VF written before operands are read; `SHL` unmasked |
| cwithmichael | 18 | `cpu.py:172-176` — VF assigned before the sum is stored |
| debugloop | 18 | `emu.py:112-114` — `& 0xf0000` on an 8-bit add is always 0 |

**What the column counts.** Tests an interpreter fails *that another interpreter passes*
([`adjudicate.py`](src/vaudit/tasks/chip8/adjudicate.py)). So `craigthomas`'s **0** means nothing
in this population contradicts it — not that it passes every test in the suite. A test that every
interpreter fails is evidence against none of them and is not counted here.

Population: seven Python CHIP-8 interpreters found by GitHub search, permissively licensed and
adaptable to a headless harness. **Not random, not cross-language, not a rate.** All seven produce
identical output on the quirk-free control, so the adapters run them correctly; and each
interpreter's failures trace to at least **one** confirmed defect in its own source
(`ADAPTERS.md`) — one traced cause per interpreter, not an accounting of every individual mark.

What this supports is narrow: **when choosing a reference implementation for differential grading,
correctness cannot be assumed from the fact that something is a working, published interpreter.**

### 4.6 SSIM ranks a blank screen above a correct implementation — when the divergence *moves* something

The comparison §5 lists as blocked over a population. It runs here on one authored ROM.

**Setup.** `shift.ch8` (16 bytes, authored, pre-registered in Amendment 3 before the bytes
existed, accepted against four gates before any strategy touched it). It isolates the `8XY6`
quirk: the COSMAC VIP shifts VY into VX, CHIP-48 and SUPER-CHIP shift VX in place. Both are
defensible and real interpreters do both. The ROM draws the font glyph `0` at an x position
computed by that shift, so a correct interpreter draws the same 14 pixels at **x=4** or **x=8**.

The seven third-party interpreters produce **two distinct correct frames**, split 2 / 5. Seven
implementations is not seven data points: on this ROM there are exactly two behaviours, and every
number below is a comparison between those two frames. Reference is `craigthomas`, the only
member with no peer-contradicted failures — the *role* Mesen2 plays for GBA Eval there, on far
weaker evidence here.

| candidate | exact | pixel proportion | thresholded τ=.05 | GMSD | SSIM |
| --- | --- | --- | --- | --- | --- |
| `craigthomas` (VIP) — reference | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `robertolaru` (VIP) | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 5 × CHIP-48 behaviour — **correct** | 0.0000 | 0.9863 | 1.0000 | 0.8492 | **0.9375** |
| CHEAT: blank screen | 0.0000 | **0.9932** | 1.0000 | **0.8730** | **0.9688** |
| CHEAT: inverted palette | 0.0000 | 0.0000 | 0.0000 | **1.0000** | −0.0160 |

**Pixel proportion, SSIM and GMSD all score the blank screen above the correct implementation.**
Thresholded at τ=.05 accepts everything except inversion, including the blank screen.

**What is new here and what is not.** The pixel-proportion result is a **replication**: GBA Eval
reported exactly this ("an emulator that just renders a white screen scores above 99%"), and the
only contribution is reproducing it on a different console with a quirk difference rather than a
hypothetical. The GMSD inversion result is a **known property of the measure**, not a discovery —
gradient magnitude is invariant under inversion by construction — though it does not appear to be
noted in the grading-iteration post, which rejected GMSD for a different reason. The SSIM result
is the one that is new, and only in the narrow sense given below.

**The SSIM mechanism, because it is not a bug in my implementation.** Block SSIM over 8×8 blocks:
moving the glyph four pixels disturbs **two** blocks — the one it left and the one it entered —
while erasing it entirely disturbs **one**. A metric that pools over blocks therefore penalises
relocation more than deletion. That is a property of the measure, not of this ROM.

**Scope, and this matters.** GBA Eval runs SSIM on 240×160 colour frames of real games, where a
sprite displacement disturbs a very different fraction of the image than a 14-pixel glyph does on
a 64×32 monochrome display. **This is not a claim that their grader mis-ranks their submissions.**
It is a demonstration that the metric they settled on has a regime where it does, that the regime
is reachable with a legitimate quirk difference, and that nothing in the metric announces when you
are in it. Whether their frames sit in that regime is measurable, and is not measured here.

**GMSD scores a wholly inverted frame at exactly 1.0000.** Gradient magnitude is invariant under
inversion — |∇(1−x)| = |∇x| — so every edge is in the same place and the metric reports perfect
similarity for an image wrong in every pixel. Explainable, reproducible, and fatal as a grader.

#### ROM B: the same test where the divergence does not move

ROM B (`digit.ch8`, 34 bytes, same four gates) isolates the `FX55`/`FX65` index quirk and draws a
**different digit in the same place** — `3` or `0`, both 14 lit pixels at (0,0). ROM A relocates a
glyph; ROM B substitutes one. Prediction 14 was registered before running it: if §4.6's mechanism
is right, SSIM should treat ROM B's divergence more favourably, because it disturbs one block
rather than two.

| | ROM A (relocation) | ROM B (substitution) | blank screen |
| --- | --- | --- | --- |
| pixel proportion | 0.9863 ✗ | **0.9980** ✓ | 0.9932 |
| SSIM | 0.9375 ✗ | **0.9943** ✓ | 0.9688 |
| GMSD | 0.8492 ✗ | 0.9331 ✗ | 0.8977 · *inverted scores 1.0000* |
| exact match | 0.0000 ✗ | 0.0000 ✗ | 0.0000 |
| separates at n=7? | **none of the five** | pixel proportion ✓, SSIM ✓ | — |

**Prior art, stated before the result.** SSIM's sensitivity to small translations is documented in
the image-quality literature and CW-SSIM exists specifically to fix it. The mechanism below is
therefore textbook, and Predictions 12, 14, 15 and 16 confirm a published property in a new
setting rather than discovering one. What is not in that literature is the *consequence* for a
reference-based grader: that it ranks a correct implementation below a blank screen.

**Prediction 14 holds, and it corrects the headline.** SSIM does not fail on structural difference
in general: it rises from 0.9375 to 0.9943 and now clears the blank screen, separating cleanly.
The failure is specific to **spatial displacement**, and the mechanism given above is the reason —
moving a glyph disturbs the block it left *and* the block it entered, while deleting or
substituting one disturbs only the block it occupied.

So the accurate statement is narrower and more useful than "SSIM ranks a blank screen higher":

> **Block-pooled similarity has a mechanically predictable blind spot for divergences that move
> something. A quirk that changes *where* output is drawn is scored worse than drawing nothing;
> a quirk that changes *what* is drawn in the same place is scored correctly.**

Two strategies fail on **both** ROMs, for different reasons. **Exact match** rejects every
correct implementation that differs at all — by construction, and it is the failure GBA Eval
reported first. **GMSD** never separates, because a wholly inverted frame scores exactly 1.0000
under it; its blindness is to inversion rather than to displacement, and no choice of ROM fixes
it. **Thresholded at τ=.05** accepts the blank screen on both ROMs and so never separates either.

#### Displacement magnitude: the score tracks block count, not distance

Amendment 6 registered Prediction 15 before this family existed: if §4.6's mechanism is right,
SSIM should **not** degrade monotonically with distance, because what matters is how many blocks
the two glyph positions touch.

| displacement | blocks touched | pixel proportion | SSIM | GMSD |
| --- | --- | --- | --- | --- |
| 0 (control) | 1 | 1.0000 | 1.0000 | 1.0000 |
| 1 | 2 | 0.9922 | 0.9498 | 0.9113 |
| 2 | 2 | 0.9902 | 0.9448 | 0.8925 |
| 4 | 2 | 0.9863 | **0.9375** | 0.8492 |
| 8 | 2 | 0.9863 | **0.9375** | 0.8219 |
| 16 | 2 | 0.9863 | **0.9375** | 0.8219 |
| 24 | 2 | 0.9863 | **0.9375** | 0.8219 |
| blank screen | — | 0.9932 | 0.9688 | 0.8730 |

**Prediction 15 holds.** SSIM is flat from displacement 4 onward — a 24-pixel shift scores
identically to a 4-pixel one, six times the distance and no change in score. Pixel proportion
behaves the same way and for the stated reason: it declines while the glyph positions still
overlap, then goes constant once they separate. And SSIM sits below the blank screen at **every**
non-zero displacement, so the failure is not an artefact of the magnitude first chosen.

#### Sensitivity check: not an artefact of my implementation

*Exploratory, run after the predictions above were registered and resolved.* My SSIM uses 8×8
blocks, matching the post's description. scikit-image's default uses a 7×7 sliding window.

| case | mine (8×8 blocks) | scikit-image default | same conclusion? |
| --- | --- | --- | --- |
| ROM A, displacement 4 | 0.9375 | 0.9581 | yes |
| ROM A, displacement 24 | 0.9375 | 0.9403 | yes |
| ROM B, substitution | 0.9943 | 0.9989 | yes |
| blank screen | 0.9688 | 0.9735 | — |

Every qualitative conclusion survives the swap: the divergent candidate scores below the blank
screen on both ROM A cases and above it on ROM B, under both implementations. One difference worth
recording — the sliding-window version **does** decline mildly with distance (0.9581 → 0.9403)
where the block version is flat. So "block count, not distance" is exact for block pooling and
approximate for window pooling; the qualitative failure holds for both.

#### ROM C: a third kind, and what actually predicts the outcome

Two ROMs could not distinguish "divergence *kind* matters" from "*block count* matters" — in ROMs
A and B the two are perfectly confounded. ROM C (`wrap.ch8`, 12 bytes, same four gates) isolates
the sprite-clipping quirk by drawing the glyph at x=62: wrapping interpreters continue at x=0,
clipping ones do not. That is a **third kind** — partial addition, where the frames share most of
their content and one simply has more — with ROM B's **one-block** geometry.

| | kind | blocks | worst correct (SSIM) | blank | separates? |
| --- | --- | --- | --- | --- | --- |
| ROM A | relocation | 2 | 0.9375 | 0.9688 | **none of the five** |
| ROM B | substitution | 1 | 0.9943 | 0.9688 | pixel proportion, SSIM |
| ROM C | partial addition | 1 | 0.9688 | 0.9375 | pixel proportion, SSIM |

**Prediction 16 holds on the behavioural test and is marginal on the numeric one.** ROM C behaves
like ROM B — divergent above blank, two strategies separating — despite being a different kind,
which is what the prediction was for. But its 0.9688 sits nearly midway between the other two,
nearer ROM B by 0.0255 against 0.0313. Reported as marginal rather than clean.

**ROM C produced three distinct frames, and the third is a bug — now verified.** `robertolaru` and
`cwithmichael` place the wrapped columns one row lower than the other wrapping interpreters. Both
compute the framebuffer position as a single linear index (`(x + i + (y+h)*64) % 2048`), so when
`x + i` reaches 64 it rolls into the next row rather than back to column 0 of the same one.

Confirmed causally rather than by inspection: a one-row `0xFF` sprite drawn at x=62 must occupy a
single scanline. Both put columns 62–63 on row 0 and the remaining six pixels on **row 1**. Three
interpreters wrap within the row, two clip at the edge — both defensible — and these two do
neither. They are excluded from ROM C's correct population, which leaves two behaviours and does
not change the numbers above, since the clipping group was already the worst correct score.

**ROM C found a defect the available suite ROMs did not.** The only ROM in `chip8-test-suite`
covering sprite edge behaviour is the quirks ROM, which is timer-dependent and excluded under Amendment 2
rule 3. An authored ROM built to probe one quirk surfaced a fifth traced bug in two interpreters
that had passed everything else available here — which is an argument for authored probes that
this project did not set out to make.

**The eligibility rule changes the conclusion** — the flip Amendment 4 said to report as the
finding rather than resolve:

| | separating threshold exists? |
| --- | --- |
| strict, n=1 (`craigthomas` alone) | exact match ✓, pixel proportion ✓, SSIM ✓ |
| extended, n=7 | **none of the five** |

Evaluated against a single reference, three of five strategies look sound. Evaluated over a
population containing one legitimate variation, none do.

**This is expected by construction and is reported as a demonstration, not a discovery.** At n=1
the population is the reference itself, which every strategy scores 1.0 by definition, so "no
correct implementation is rejected" is vacuously true — there is only one and it is the yardstick.
The flip is worth showing because the vacuity is not visible in the output: the n=1 table reads
like a passing grade. It is the argument for measuring over a population made concrete, not
evidence for it.

**Two of four cheats were degenerate.** ROM A settles at frame 2, so `frozen_first_frame` and
`one_frame_late` are byte-identical to the reference and uncatchable by anything. Amendment 4
named that possibility before the run; they are excluded from separation and reported, not
replaced with cheats chosen after seeing the numbers.

### 4.7 Prediction scorecard

| # | prediction | outcome |
| --- | --- | --- |
| 1–8 | the EvalPlus and replication-task predictions | superseded by Amendments 2–4; not evaluated |
| 9 | quirks ROM with n ≥ 3 | **unrun** — that ROM is timer-dependent and excluded |
| 10 | exact match accepts only the reference's quirk; `honest_pass` < 1.0 | **hit** — 2/7 |
| 11 | pixel proportion: both scores > 0.98, no separating threshold | **hit**, and the figures landed where predicted (0.9863 / 0.9932) |
| 12 | SSIM ranks a correct interpreter below a structure-preserving cheat | **hit** — 0.9375 vs 0.9688 |
| 13 | GMSD does not reproduce its reported failure; ranks like SSIM | **miss** — they agree on blank-vs-correct and disagree totally on inversion (1.0000 vs −0.0160). GMSD fails here, differently |
| 14 | SSIM scores the divergence higher on ROM B than on ROM A (one disturbed block, not two) | **hit** — 0.9375 → 0.9943, clearing the blank screen and separating. Confirms the mechanism and scopes the finding to displacement |
| 15 | SSIM does not degrade monotonically with displacement; 4px and 24px within 0.02 | **hit** — identical at 0.9375 for 4, 8, 16 and 24. Block count predicts the score; distance does not |
| 16 | a third divergence *kind* with one-block geometry behaves like ROM B, not ROM A | **marginal hit** — separates like ROM B and scores above its blank screen, but 0.9688 sits nearly midway between the two, nearer B by 0.0255 vs 0.0313 |

| 17 | the boundary is `φ > 0.5`, independent of density | **miss** — the derivation dropped the collision term. Corrected in Amendment 10 to `φ(1−d) > ½` |
| 18 | SSIM's φ-crossover is below pixel proportion's | **miss**, and the wrong question: φ is not SSIM's parameter at all |
| 19 | at GBA scale, one displaced sprite, the blank frame loses under all three | **hit** — and the costliest hit here. SSIM 0.9870 vs 0.3033. §4.6's relevance to GBA Eval is materially reduced, as pre-committed |
| 22 | the corrected curve predicts four held-back densities to ±0.04 | **miss**, narrowly — three inside ±0.01, the fourth off by 0.049. Errs low at high density, as registered |
| 23 | block occupancy, not density, controls SSIM — and flips a verdict | **split** — mechanism confirmed hard (blank scores 0.9683 vs 0.0027 at identical density), no verdict flipped, so falsified as written |

| 20 | ROM D: a second relocation quirk fails exactly like ROM A | **hit** — identical figures, 0.9375 vs 0.9688, nothing separates |
| 21 | ROM E: a second substitution quirk separates exactly like ROM B | **hit** — 0.9943 and 0.9980, both above blank |

Fourteen evaluated, eight hit, one marginal, one split, four missed. The Amendment 8/10 study
falsified four of its five predictions, including both registered out of sample, and is the most
useful thing in this document for exactly that reason: it replaced a scope concession with a
closed-form boundary, and it cost the headline its generality. **#13 was registered as one I expected to get wrong**, and
it is the one that produced the sharper finding. **#14 was registered specifically so that a
mechanism I had already published in §4.6 could be falsified** — it could have shown the
explanation was wrong while the headline number stood. It did not, and the claim is narrower and
better for having been put at risk.

---

## 5. What still could not be run

§4.6 is that comparison, on one authored ROM. What remains blocked, and why — each measured:

1. **Correct implementations are rare in this sample.** 1 of 7 (§4.5). A population of one supports
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

**Prediction 9 is unrun** and stands pre-registered and unresolved rather than dropped; 10–13
were evaluated in §4.7. The
eligibility rule was amended twice, both before any metric existed, both recorded with reasoning —
including that Amendment 1 was made *after* the strict rule returned an unusable answer, by the
same party that would write the metrics.

---

## 6. Rejected hypotheses — do not re-test

1. **Hardening over-tightens EvalPlus graders.** No. Delta 0.00 across 5 tasks.
2. **`honest_pass` on stock EvalPlus is informative.** No — the oracle is a strict superset of the
   grader, so it is ~1.0 by construction.
3. **Agreement with my reference indicates correctness.** No; the ROM's own marks had to adjudicate.
4. **Raw mark counts adjudicate a test ROM.** No — the failure glyph also occurs inside the label
   text, producing a uniform false `err=8` for every interpreter including the reference.
5. **Forcing the quirks ROM's platform removes its timer dependence.** No.
6. **Third-party quirk flags substitute for a quirk-exercising ROM.** No.
7. **GMSD behaves like SSIM on a monochrome display** (Prediction 13). No — it scores a wholly
   inverted frame at 1.0000, because gradient magnitude is invariant under inversion.
8. **A grading strategy can be evaluated against a single reference.** No. Three of five separate
   cleanly at n=1 and none do at n=7; the reference-only evaluation says nothing.

## 7. Limitations

- §4.1 denominators are 4–8 mutants per task, capped; n=5 tasks. §4.3 is a pilot on an authored
  task. §4.5 is a convenience sample of seven.
- Timer semantics are **not** normalised across the CHIP-8 population and cannot be without
  rewriting those projects.
- `4c` ran only as a hand-verified pilot; `4b′` is an instrumentation helper plus a checklist
  demonstrated on two graders, not a generic checker.
- Games were never tried as quirk-exercising ROMs (§5, item 3).
- §4.6 runs on **one authored 16-byte ROM** and one quirk, with a 14-pixel glyph on a 64×32
  monochrome display. GBA Eval's frames are 240×160 and in colour, where the same displacement
  disturbs a different fraction of the image. The finding is that the regime exists and is
  reachable by a legitimate quirk difference, not that their grader mis-ranks their submissions.
- §4.6 covers two divergence *kinds* (relocation, substitution) on one quirk each. It does not
  vary magnitude within a kind — a two-pixel or twenty-pixel shift is untested — nor does it test
  more than one quirk per kind.

---

## 8. What would make this a real study

1. **More authored ROMs, same discipline.** §4.6 already did this three times, and the method is
   the part that is settled: a ROM is an **input**, not a member of the population, so authoring
   one keeps the population third-party — which is what GBA Eval does when it picks which games to
   replay. The risk is tuning the input until a chosen strategy fails, and the mitigation used was
   pre-registration: exact design and prediction committed before the bytes, four acceptance
   gates, source published beside the bytes. What is missing is **coverage**: one quirk per
   divergence kind, and magnitude varied only for displacement (§7).
2. **Try real games as quirk-exercising ROMs** (§5, item 3). Untried, plausibly sufficient, and
   entirely third-party — strictly better than authoring one if it works.
3. **Three or more fully-clean interpreters**, at roughly a dozen more adaptations.
4. Then Predictions 1–9, unchanged, against the five strategies.

## 9. Reproduce

```bash
uv sync
python -m vaudit.tasks.chip8.fetch    # population + ROMs at pinned commits (network, no API key)
make check                            # 173 tests, offline, no API key
python -m vaudit.audit.sweep --tasks 5  # prices the run; buys nothing without --confirm
git config core.hooksPath .githooks   # activate the pre-commit gate (incidents #2, #17)
```

**Order matters, and an earlier draft had it wrong.** Run `make check` before fetching and you get
**124 passed, 19 skipped** — the adapter tests skip cleanly when the population is absent, by
design, so the suite can never go green while silently claiming a study that did not run. Only
after fetching is it **173**. The draft listed the steps the other way round and claimed the
fetched count for the unfetched one; that is incident #14, and the counts here were re-measured
in both orders on 2026-09-17 rather than carried forward.

**Verified from a clean clone on 2026-09-16**, which is how #12 and #13 were found: `make check`
was failing on the format step while `ruff check` alone reported success. Steps 1, 2 and 3 now
pass from a fresh clone with no API key and no pre-existing `.population`. Step 4 was run as a
dry run only; it prints the estimate and buys nothing.

Three caveats. §4.2 has no reproduce path in this repository at all (see that section);
`.githooks` is not active in a fresh clone — `git config core.hooksPath .githooks` is required,
and that is incident #2. Worse, until 2026-09-17 there was no `.githooks` directory here at all,
so that command set a config pointing at nothing and the gate had never run in this repository —
incident #17. The hook exists as of this commit and runs `make check` unpiped, which is #3. And
§4.1/§4.2 were produced in the predecessor repository
before the clean-room rewrite. §4.1 has since been regenerated **in this repository**
(2026-09-17) and its population is committed under `data/solutions/`, so it now reproduces with no
API calls. §4.2 remains predecessor-only.

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
| 14 ▲ | "`make check` — 155 tests" | in the documented order it was 111 passed, 14 skipped; the population has to be fetched first. The suite has grown since — §9 carries re-measured counts | running the steps as written, in the order written |
| 15 ▲ | "the sweep command reproduces §4.1 and §4.2 here" | true of §4.1, false of §4.2 — the clean-room rewrite dropped the hardening track, so this repo cannot produce that number at all | checking what the shipped sweep actually measures before running it |
| 16 ▲ | "the repository flipped to public on its own — an incident" | it did not. The owner made it public, deliberately, using an option I had offered them. I recorded a defect that never existed and then reverted their decision | the owner said so |
| 17 ▲ | §9: "`git config core.hooksPath .githooks` — activate the pre-commit gate" | there was no `.githooks` directory in this repository. The command set a config pointing at nothing, exited 0, and the gate had never run here — #2 with the hook files missing too | checking whether the gate was on, immediately before a commit that would have relied on it |

#12, #13, #14 and #17 were found by running or checking §9's own commands, which is why that is
now part of the procedure rather than an assumption. #13 is the sharpest of the set: a tool whose
job is maintaining quality silently modified the evidence, in a document arguing that
measurements are confidently about the wrong thing. Quoted source is now fenced as `text` so no formatter can
touch it.
