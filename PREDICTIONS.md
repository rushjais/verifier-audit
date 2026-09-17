# PREDICTIONS — M1c, registered before the study runs

Committed **before** any grading strategy is implemented or any score computed. The git history
is the proof of ordering; check the commit date of this file against the commit that adds
`tasks/chip8/`.

**Why this file exists.** Whoever writes both the population and the metrics can produce any
result they want. The M1b replication pilot is the cautionary example and it was mine: the spec
gap was authored, and during the clean-room migration a sandbox bug silently turned every run
into a failure, which would have read as "every cheat is caught". Predictions written in advance,
with misses reported as loudly as hits, are the cheapest defence against both.

---

## Setup being predicted

- **Population (correct):** k independently written open-source CHIP-8 interpreters, fetched by
  pinned commit, never vendored, licence recorded per entry. They disagree on documented quirks —
  `8XY6`/`8XYE` shift source, `FX55`/`FX65` index increment, `BNNN` jump offset, sprite wrapping,
  VF reset on AND/OR/XOR — and both sides of each quirk are defensible. **None written by me.**
- **Population (cheats, mine, and obviously so):** blank screen, frozen first frame, inverted
  palette, correct-but-one-frame-late.
- **Reference:** one interpreter designated as the Mesen2 analogue.
- **ROMs:** freely distributable test programs only. At minimum a quirk-free one (IBM logo) and a
  quirk-exercising one (chip8-test-suite quirks ROM). No commercial ROMs, ever.
- **Strategies:** exact match, pixel proportion, thresholded match, GMSD, SSIM.

**The question each strategy is scored on:** is there *any* acceptance threshold at which it
accepts every correct interpreter and rejects every cheat? Reporting separation rather than a
rate at one arbitrary threshold avoids smuggling in the answer through the threshold.

---

## Predictions

| # | prediction | confidence |
|---|---|---|
| 1 | **Exact match separates on the quirk-free ROM and fails on the quirks ROM.** Quirk-divergent-but-correct interpreters produce different frames, so `honest_pass` collapses toward 0 there. | high |
| 2 | **Pixel proportion fails on catch, badly.** CHIP-8 is 64×32 monochrome and typical frames are mostly off-pixels, so a blank screen scores **> 0.8** against the reference. No separating threshold exists. | high |
| 3 | **Thresholded match beats exact but still has no separating threshold on the quirks ROM.** Quirk differences are structural, not noise, so no single τ is both permissive enough for them and strict enough for the cheats. | medium |
| 4 | **GMSD's reported failure does NOT reproduce.** Their GMSD problem was sparse single-pixel noise that the eye integrates out. A 64×32 monochrome display with no antialiasing has no such regime, so GMSD should behave much like SSIM here. | medium-low |
| 5 | **SSIM separates best of the five, and still fails to accept every correct interpreter on the quirks ROM.** | medium |
| 6 | **Rotating the reference changes `honest_pass` by at least one implementation under exact match**, and by less under SSIM. | medium |
| 7 | **Headline: no strategy achieves `honest_pass` = 1.0 and `catch_rate` = 1.0 simultaneously on the quirks ROM.** | medium-high |
| 8 | **The reason is that quirk disagreement is semantic, not perceptual.** Perceptual metrics repair perceptual divergence; they cannot repair two interpreters that correctly did different things. If 5 and 7 hold for this reason, it is a real limitation of the SSIM approach and the most interesting thing here. | medium |

## What would falsify each

1. Exact match accepts ≥ 2 correct interpreters on the quirks ROM.
2. Blank screen scores < 0.5, or some threshold separates cleanly.
3. Some τ accepts all correct and rejects all cheats on the quirks ROM.
4. GMSD's separation is materially worse than SSIM's (≥ 1 implementation difference).
5. SSIM accepts every correct interpreter on the quirks ROM.
6. `honest_pass` is identical under every choice of reference.
7. Any strategy achieves both rates at 1.0.
8. Strategies 4/5 accept quirk-divergent interpreters, meaning the divergence was perceptual after all.

## Reporting rules

- Every prediction gets an explicit **hit / miss / inconclusive**, in the writeup, in this order.
- A miss is reported at the same prominence as a hit. Prediction 4 is the one I most expect to
  miss, and it is here precisely so that saying so afterwards costs nothing.
- Counts beside every rate. `honest_pass = 3/7` is a number; `0.43` on its own is not.
- If k < 5 usable interpreters can be found under permissive licences, say so and report the
  smaller n rather than padding the population with implementations I wrote.
- The cheat submissions are mine and are labelled as mine everywhere they appear.

---

# AMENDMENT 1 — per-ROM eligibility (2026-09-16)

**Written before any grading strategy exists or any metric has been run.** Commit order is the
evidence, as with the original.

## What changed

Eligibility for the correct-implementation population was global: an interpreter had to pass the
whole correctness suite. It is now **per-ROM**: an interpreter is eligible for the comparison on
ROM X if it is correct *for what ROM X exercises*.

## Why, and the part that should make you suspicious

Four independently written third-party interpreters were adapted. By the suite's own verdict:
`craigthomas` 0 failures, `wyattferguson` 8, `islay` 18, `debugloop` 18. Under the global rule
the eligible population was **1**, which cannot support honest-pass over a population and cannot
support rotating the reference. The study could not run.

So this change was made *after* the strict rule returned an unusable answer, by the same person
who will write the metrics. That is the shape of a rationalisation whether or not it is one, and
it is why this is written down before anything is measured rather than explained afterwards.

The argument that it is nevertheless correct: **correctness is relative to what is being
tested.** An interpreter with a vF bug is entirely correct for a ROM that never touches vF, and
GBA Eval would not discard an emulator's video score over an audio fault. The question this study
asks — do grading strategies rank correct-but-different implementations sensibly — is a question
about a specific ROM's output, so the correctness that matters is correctness on that ROM.

## The rule

- **ROM reports its own verdict** (corax+, flags): eligible iff zero failed tests that a peer
  passes. The ROM adjudicates; my reference does not.
- **ROM reports nothing** (ibm-logo, chip8-logo, quirks): eligible iff the interpreter agrees
  with the consensus on the quirk-free control ROMs, i.e. its core execution is demonstrably
  sound. A ROM without self-reported verdicts cannot adjudicate itself.

## What this costs, stated plainly

The second clause is **weaker than it looks, and weakest exactly where it matters most**. An
interpreter can agree on ibm-logo and still be buggy in a way the quirks ROM would expose — and
the quirks ROM is the one the whole study turns on. So a disagreement there may be a legitimate
quirk choice or may be a bug, and this rule cannot tell them apart.

Mitigations, all of which are obligations on the writeup and not optional:

1. Every result table carries each interpreter's **global** failure count beside its per-ROM
   eligibility, so nothing is hidden behind the relaxation.
2. Any headline claim resting on the quirks ROM is reported with the caveat that its population
   is eligible-by-proxy, not eligible-by-verdict.
3. If a strategy's ranking flips depending on which rule is used, that is reported as the
   finding, not resolved by picking the friendlier one.

## Predictions this does not change

1 through 8 stand as written. The population they are evaluated over is now larger and weaker,
which should if anything make the differential-grading failures *easier* to observe — so a null
result under this rule is stronger evidence against the predictions, not weaker.

---

# AMENDMENT 2 — tightening Amendment 1, and the ROM set (2026-09-16)

Written before any grading strategy exists or any metric has been run. Supersedes Amendment 1
where they conflict.

## Why Amendment 1 was too loose

Amendment 1 let a non-self-verifying ROM (ibm-logo, chip8-logo, quirks) accept any interpreter
that agreed with the consensus on the quirk-free controls. It named that as the weak point and
it was: agreeing on ibm-logo does not show an interpreter is sound in the ways the quirks ROM
probes, and the quirks ROM is the one the study turns on. The relaxation delivered n=4 on exactly
the ROM where the evidence was thinnest, which is the wrong way round.

## The rule, tightened

1. **Per-ROM eligibility applies only to self-verifying ROMs** — those that render their own
   pass/fail marks (corax+, flags). There the ROM adjudicates: zero failed tests that a peer
   passes.
2. **Non-verifying ROMs require a fully clean implementation** — zero failures across the whole
   correctness suite. Proxy eligibility is withdrawn.
3. **Timer-dependent ROMs are excluded entirely.** Timer semantics are not normalised across this
   population and cannot be without rewriting the projects, so a ROM whose output depends on them
   is not comparable here.

## Both outcomes, reported

| rule | corax+ | flags | ibm-logo | chip8-logo | quirks |
|---|---|---|---|---|---|
| original (global clean) | 1 | 1 | 1 | 1 | 1 |
| Amendment 1 (proxy) | 2 | 1 | 4 | 4 | 4 |
| **Amendment 2 (this one)** | **2** | **1** | **1** | **1** | **excluded** |

(Counts exclude my own reference, which is the yardstick and not a population member.)

## Confirming the quirks ROM — it does not qualify

Required before running metrics, and the answer is no.

`5-quirks.8o` contains nine delay-timer references, and they are not incidental: they implement a
**frames-per-second detection routine** (lines 632–683, 745–761) that reads the delay timer in a
loop to measure how fast the interpreter runs, in order to test the display-wait quirk. The ROM
is therefore timer-dependent in the strongest possible sense — it is *measuring* timing.

This population disagrees about timer semantics by construction: `craigthomas` decrements on
demand, `wyattferguson` once per `cycle()`, `debugloop` every fifth cycle via a counter it never
resets (so past the fifth, on every cycle), `islay` on demand. Under rule 3, **the quirks ROM is
excluded.**

## What that leaves, stated plainly

No ROM currently has both an eligible population of n ≥ 2 **and** genuine disagreement within it:

- corax+ has n=2, and those two (`craigthomas`, `wyattferguson`) produce **identical** frames.
- every other ROM has n=1.

So M1c as designed cannot run yet. That is a finding about the difficulty of the setup rather
than a result about grading strategies, and it is recorded as such. It is not grounds for
loosening the rule a second time; Amendment 1 already shows where that leads.

## Pre-registered prediction for the quirks ROM

Registered now so that if the ROM ever becomes usable — via interpreters whose timer semantics
can be shown to agree, or a timer-free quirk ROM — the prediction predates the run.

> **Prediction 9.** On a quirk-exercising ROM with an eligible population of n ≥ 3, exact-frame
> matching against any single reference will accept at most one correct interpreter
> (`honest_pass ≤ 1/n`), because quirk divergence changes what is drawn rather than how it looks.
> SSIM will accept more than exact match but still fewer than all, for the same reason: it
> repairs perceptual divergence, not semantic divergence.
>
> **Falsified if** exact match accepts two or more, or SSIM accepts every eligible interpreter.
> **Confidence:** medium.

## Pre-registered ROM set

Fixed now; additions require a further dated amendment. Source: `Timendus/chip8-test-suite`
@ `742e9eac`, GPL-3.0, fetched and never redistributed.

| ROM | role | timer-dependent | self-verifying | in the study |
|---|---|---|---|---|
| 1-chip8-logo | quirk-free control | no | no | yes |
| 2-ibm-logo | quirk-free control | no | no | yes |
| 3-corax+ | correctness | no | yes | yes |
| 4-flags | correctness | no | yes | yes |
| 5-quirks | disagreement | **yes** | no | **excluded** |
| 6-keypad | — | yes | yes | excluded: needs live input |
| 7-beep | — | yes | no | excluded: audio, timer-dependent |
| 8-scrolling | — | no | no | excluded: SUPER-CHIP only |

---

# AMENDMENT 3 — an authored quirk ROM, pre-registered (2026-09-17)

**Written before any ROM bytes exist.** The commit that adds `src/vaudit/tasks/chip8/quirk_roms.py`
must be later than this one; commit order is the evidence, as with Amendments 1 and 2.

## Why authoring a ROM is legitimate, and where the line is

The population must stay third-party — that rule is not being relaxed. A ROM is not a population
member; it is an **input**. The interpreters are what is measured; the ROM is what they are
measured *on*. GBA Eval chooses which games to replay, and choosing an input is not the same as
authoring the subject.

The real risk is different and worth naming: **an input can be tuned until a chosen strategy
fails.** Three guards, all checkable from the git history:

1. This document fixes the design before the bytes exist.
2. The ROM is accepted or rejected against criteria stated below (§ Acceptance), **before any
   grading strategy is run on it**.
3. Once any strategy has been run, the ROM is frozen. Changing it afterwards voids the study and
   requires a new amendment saying so.

The `.8o` source ships beside the bytes so anyone can read what it does.

## ROM A — `shift.ch8` — a small, localised divergence

Isolates the `8XY6` shift quirk. The COSMAC VIP shifts VY into VX; CHIP-48 and SUPER-CHIP shift
VX in place. Both are defensible and real interpreters do both.

```text
0x200  6110   V1 = 0x10
0x202  6208   V2 = 0x08
0x204  8126   V1 = shift      ; VIP: V1 = V2>>1 = 4    CHIP-48: V1 = V1>>1 = 8
0x206  6000   V0 = 0          ; digit 0
0x208  F029   I  = font(V0)   ; portable: asks the interpreter for its own font address
0x20A  6300   V3 = 0
0x20C  D135   draw glyph at (V1, V3), 5 rows
0x20E  120E   jump self
```

Expected divergence: the 14-pixel glyph is drawn at **x=4** or **x=8** — a four-pixel horizontal
shift. Roughly 28 of 2048 pixels differ; nothing else on the display changes.

## ROM B — `digit.ch8` — a larger, structural divergence

Isolates the `FX55`/`FX65` index quirk: whether `I` is left advanced after a block store/load.
After a store, a subsequent load reads from a different address under each behaviour, yielding a
**different digit glyph** rather than the same glyph moved.

Exact opcodes are not fixed here because the data bytes depend on the assembled layout. What *is*
fixed: the ROM must differ **only** in which digit is rendered, at a single fixed position, with
both digits drawn from the interpreter's own font via `FX29`.

## Acceptance — the ROMs must pass this before any strategy is run

A ROM enters the study only if all four hold. Failing any one means it is rewritten or abandoned,
and that is recorded.

1. **Timer-free.** Identical final frame with timer ticks enabled and disabled (the check that
   excluded `5-quirks.ch8` under Amendment 2 rule 3).
2. **Quirk-sensitive in exactly one dimension.** Flipping the target quirk changes the frame;
   flipping each of the other four does not.
3. **Settled.** The frame is stable from some frame count onward, so the result does not depend
   on how long it is run.
4. **Real on third-party interpreters.** At least two population members, differing on the target
   quirk, reproduce the predicted divergence. A ROM that only works on my own reference is a ROM
   that tests my reference.

## Predictions

Registered now. Prediction 9 (Amendment 2) stands unchanged and is evaluated on these ROMs.

> **Prediction 10 — exact match.** On ROM A, exact frame matching accepts only interpreters whose
> shift behaviour matches the reference's, so `honest_pass` equals the fraction of the eligible
> population sharing the reference's quirk — and is strictly below 1.0 whenever the population
> contains both behaviours.
> **Falsified if** exact match accepts an interpreter with the opposing quirk.
> **Confidence:** high — this is close to definitional, and it is registered mainly as a check
> that the harness is wired correctly.

> **Prediction 11 — pixel proportion discriminates nothing here.** A four-pixel shift of a
> 14-pixel glyph leaves ~28 of 2048 pixels differing, so the proportion-of-correct-pixels score
> for a correct-but-divergent interpreter is **> 0.98**. A blank screen also scores **> 0.98**,
> because the display is mostly off. **No threshold separates the two.**
> **Falsified if** some threshold accepts every correct interpreter and rejects the blank cheat.
> **Confidence:** high for the two scores; medium for "no threshold separates", which depends on
> the cheat set.

> **Prediction 12 — SSIM rejects a correct interpreter on ROM A.** A four-pixel shift moves
> structure, not just intensity, so SSIM scores it well below the near-1.0 it gives a
> perceptually-identical frame. SSIM will therefore rank a correct-but-divergent interpreter as
> worse than at least one cheat that leaves structure intact.
> **Falsified if** SSIM scores the shifted glyph above every cheat.
> **Confidence:** medium. This is the prediction the study exists to test — it is Prediction 8's
> claim that perceptual metrics repair perceptual divergence but not semantic divergence.

> **Prediction 13 — GMSD does not reproduce its reported failure here.** GBA Eval's GMSD problem
> was sparse single-pixel noise pooled by standard deviation. A 64×32 monochrome display has no
> antialiasing regime to produce that, so GMSD and SSIM should rank these candidates nearly
> identically.
> **Falsified if** GMSD and SSIM disagree on the ordering by more than one position.
> **Confidence:** medium-low. Registered because I expect to be wrong, and saying so beforehand
> costs nothing.

## Reporting rules

- Every prediction gets **hit / miss / inconclusive**, misses at the same prominence as hits.
- Counts beside rates; `honest_pass = 2/4` is a number, `0.5` alone is not.
- Each result states the eligible population for that ROM and each member's global failure count
  (Amendment 1, obligation 1).
- If ROM B cannot be assembled to satisfy Acceptance, the study runs on ROM A alone with n
  reported, rather than being widened until something works.

---

# AMENDMENT 4 — report both eligibility rules (2026-09-17)

Written before any grading strategy exists. **No rule changes.**

ROM A is accepted (Amendment 3, all four gates) and the population splits 2/5 on the shift quirk.
But ROM A renders no pass/fail marks, so under Amendment 2 rule 2 it is non-self-verifying and
admits only fully-clean implementations — `craigthomas` alone, n=1.

There is an argument for extending the rule: ROM A executes five opcodes with no branching and no
data dependence, so its correct output is **analytically determined**, and Amendment 3 stated that
output — a 14-pixel `0` glyph at x=4 or x=8, nothing else — *before the ROM ran*. An interpreter
producing it has demonstrably executed every opcode this ROM uses. That is verification by
pre-stated specification rather than by rendered marks, and `2-ibm-logo` would not qualify because
nobody derived its output by hand.

**That extension is not being made.** It would be the third loosening, it arrives exactly when the
strict rule blocks the study again, and it would be made by the party that benefits. Amendment 1
is the standing example of where that leads.

Instead, every result is reported under **both** rules:

| rule | population for ROM A | n |
| --- | --- | --- |
| strict (Amendment 2 rule 2) | `craigthomas` | 1 |
| extended (analytically determined output) | all seven that reproduce a predicted frame | 7 |

Per Amendment 1 obligation 3: **a ranking that flips between the two rules is reported as the
finding, not resolved by choosing the friendlier one.** If the two agree, the strict number is the
headline and the extended one is corroboration.

## Cheat set, fixed now

`BlankScreen`, `FrozenFirstFrame`, `InvertedPalette`, `OneFrameLate`, as already implemented.
Noted in advance: ROM A settles at frame 2, so `FrozenFirstFrame` and `OneFrameLate` may be
degenerate here — identical or near-identical to a correct frame. If so that is reported, not
patched by adding cheats until the numbers look better.

## Threshold handling

Each strategy returns a similarity in [0, 1]. A strategy is scored on **separation**: does any
acceptance threshold accept every eligible correct interpreter and reject every cheat? Reporting
separation rather than a rate at one chosen threshold avoids smuggling the answer in through the
threshold.
