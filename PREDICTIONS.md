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

---

# AMENDMENT 5 — ROM B accepted; Prediction 14 (2026-09-17)

**Ordering, stated precisely.** ROM B's *design* was pre-registered in Amendment 3, which fixed
its intent and constraint and explicitly deferred the bytes ("the data bytes depend on the
assembled layout"). This amendment and ROM B's bytes landed in the **same commit**, so unlike
ROMs A and the Amendment 6 family, the bytes were not committed after their own amendment. What
*was* registered before being run is Prediction 14, which is the claim at risk. Recording the
difference rather than implying a stricter sequence than happened.

ROM B (`digit.ch8`, 34 bytes) is assembled and passes all four Amendment 3 gates: timer-free,
sensitive to `memory_increments_i` and inert to the other four quirks, settled at frame 2, and
reproduced by all seven third-party interpreters.

It draws **a different digit in the same place** — `3` under the VIP behaviour, `0` under
CHIP-48, both 14 lit pixels at (0,0). ROM A moves one glyph; ROM B substitutes another. Same-block
structural change versus cross-block relocation.

The population splits differently from ROM A, which is worth recording: `robertolaru` follows the
VIP shift but not the VIP index behaviour, and `cwithmichael` the reverse. Real interpreters mix
their quirk choices rather than adopting a platform wholesale.

| ROM | VIP behaviour | CHIP-48 behaviour |
| --- | --- | --- |
| A (shift) | craigthomas, robertolaru | wyattferguson, islay, cwithmichael, rudzen, debugloop |
| B (index) | craigthomas, cwithmichael | wyattferguson, islay, robertolaru, rudzen, debugloop |

**Registered before the strategies are run on ROM B.**

> **Prediction 14.** §3.6 explained SSIM's ROM A failure mechanically: relocation disturbs two 8×8
> blocks, deletion disturbs one. ROM B's divergence stays inside one block, so that explanation
> predicts SSIM should treat the correct-but-divergent candidate **more favourably on ROM B than
> on ROM A** — its score should rise, and it may now exceed the blank screen, letting SSIM
> separate where it could not before.
>
> **Falsified if** SSIM's score for the correct-divergent candidate on ROM B is not higher than
> its 0.9375 on ROM A.
>
> **Why this matters more than the number:** if it holds, §3.6's finding is scoped — SSIM fails on
> *relocation*, not on structural difference generally, and the mechanism given is the right one.
> If it fails, the mechanism in §3.6 is wrong and that section needs rewriting even though its
> headline number stands.
>
> **Confidence:** medium-high on the direction, low on whether it clears the blank screen.

---

# AMENDMENT 6 — varying the shift magnitude; Prediction 15 (2026-09-17)

ROM A fixes one displacement: four pixels. §3.6 attributes SSIM's failure there to *block* count —
relocation disturbs the block the glyph left and the block it entered. That explanation makes a
prediction about magnitude that is not the obvious one, so it is registered before the ROMs exist.

**The ROM family.** ROM A's opcodes generalise: `V1 = A`, `V2 = B`, `8126`. The VIP behaviour draws
at `B>>1`, CHIP-48 at `A>>1`, so choosing A and B sets the displacement. Everything else — glyph,
row, timing — is unchanged. Displacements of 0, 1, 2, 4, 8, 16 and 24 pixels, where 0 is a control
that must produce identical frames under both behaviours.

> **Prediction 15.** SSIM's score for the correct-but-divergent candidate **will not degrade
> monotonically with displacement.** If the mechanism in §3.6 is right, what matters is how many
> 8×8 blocks the union of the two glyph positions touches, not how far apart they are. A 24-pixel
> shift disturbs two blocks, exactly as a well-placed 4-pixel shift does, so the two should score
> **within 0.02 of each other** despite a 6× difference in distance.
>
> **Falsified if** SSIM decreases monotonically with displacement across 1, 2, 4, 8, 16, 24 — that
> is, if distance rather than block count predicts the score.
>
> **Confidence:** medium. The 4-wide glyph and 8-wide blocks mean small displacements can straddle
> a boundary and touch two blocks anyway, so the relationship may be ragged rather than flat. What
> is predicted is the absence of monotonicity, not a flat line.

A second thing this family settles, at no extra cost: **whether pixel proportion's failure is
magnitude-dependent.** It compares pixel-by-pixel with no blocks, so on that metric a larger
displacement should make the divergent candidate strictly worse — up to the point where the two
glyph positions stop overlapping, after which it is constant. If pixel proportion is monotone
where SSIM is not, the two failures have different causes and the write-up should say so.

---

# AMENDMENT 7 — a third quirk, and the claim it can falsify (2026-09-17)

Written before ROM C exists.

§3.6 currently describes two divergence *kinds* — relocation (ROM A) and substitution (ROM B) —
and explains the difference by **block count**: relocation disturbs the block a glyph left and the
one it entered; substitution disturbs only the block it occupies. Two ROMs cannot distinguish
"kind matters" from "block count matters", because in this sample kind and block count are
perfectly confounded.

**ROM C — `wrap.ch8`, the sprite-clipping quirk.** Draw the font glyph at x=62, hard against the
right edge. Interpreters that wrap put the overflowing columns at x=0; interpreters that clip
simply do not draw them. Both are defensible and real interpreters do both.

That is a **third kind**: not relocation and not substitution but **partial addition** — the two
frames share most of their content, and one has extra pixels somewhere the other has none. It is
also, by geometry, a **one-block** divergence: the shared columns at 62–63 are identical, and the
whole difference falls in the block covering x=0–7.

> **Prediction 16.** SSIM's behaviour is predicted by **block count alone, not by divergence
> kind**. ROM C is a different kind from both A and B but shares B's block count, so SSIM should
> score its divergent candidate **close to ROM B's 0.9943 and well above the blank screen's
> 0.9688** — and should separate, as it does on ROM B and fails to on ROM A.
>
> **Falsified if** SSIM scores ROM C's divergence below the blank screen, or nearer ROM A's
> 0.9375 than ROM B's 0.9943. Either outcome would mean kind matters independently of block count
> and the mechanism in §3.6 is incomplete.
>
> **Confidence:** medium-high. The risk is that "partial addition" changes block *variance* rather
> than block membership, which the SSIM contrast term is sensitive to in a way pure displacement
> is not.

ROM C must pass the same four Amendment 3 gates before any strategy runs on it, and the
population must genuinely split on `sprites_wrap` — a ROM on which every interpreter agrees tests
nothing.

---

# AMENDMENT 8 — the regime boundary §4.6 left unmeasured (2026-09-17)

Written before any of the code below exists.

§4.6 ends with a scope paragraph that names the objection and does not answer it: GBA Eval's
frames are 240×160 and in colour, where a displacement disturbs a different fraction of the image
than a 14-pixel glyph does on 64×32. A reader is entitled to ask whether the whole effect is an
artefact of a nearly-empty display — the blank screen is already 99.3% pixel-correct before any
metric runs. This amendment answers it.

**This is a synthetic geometric study, not a quirk study.** There is no interpreter and no ROM in
it. Its only purpose is to locate the boundary of the regime §4.6 demonstrates, so that someone
grading their own frames can tell whether they are inside it. It is labelled as synthetic
throughout and does not touch the CHIP-8 population.

**The parameter that matters is not density.** Working it analytically: let the reference frame
have `N` pixels of which a fraction `d` are lit, and let a divergence displace a fraction `φ` of
that lit content far enough not to overlap itself.

    blank frame       differs in  d·N        pixels — every lit pixel
    displaced frame   differs in  2·φ·d·N    pixels — φ·d·N vanish, φ·d·N appear

    blank scores higher under pixel proportion  ⟺  d·N < 2·φ·d·N  ⟺  φ > 0.5

So density cancels. **The governing variable is the fraction of drawn content the divergence
moves**, and §4.6 is the φ=1 corner: the glyph *is* the content, so all of it moved. This predicts
that a quirk which shifts one sprite of a busy frame has small φ and will not reproduce §4.6,
while a quirk which shifts a whole background has φ≈1 and will, at any density.

> **Prediction 17.** Pixel proportion's crossover is at **φ ≈ 0.5** and is **independent of
> density**. Sweeping φ at fixed d, the blank frame outscores the displaced frame for φ > 0.5 and
> loses for φ < 0.5.
>
> **Falsified if** the empirical crossover lies outside φ ∈ [0.40, 0.60], or if it moves by more
> than 0.10 across d ∈ [0.05, 0.50].
>
> **Confidence:** high. This is arithmetic, not an empirical guess; it is registered so that the
> implementation can be caught disagreeing with the derivation.

> **Prediction 18.** SSIM's crossover is at a **lower φ** than pixel proportion's. §4.6's
> mechanism is that block pooling penalises relocation more harshly than pixel counting does
> — two disturbed blocks against one — so SSIM should keep preferring the blank frame even when
> less than half the content moves.
>
> **Falsified if** SSIM's φ-crossover is at or above pixel proportion's, or if SSIM shows no
> crossover at all across φ ∈ [0.05, 1.0]. Either would mean §4.6's mechanism does not generalise
> beyond the sparse single-glyph case, and §4.6 would have to be rewritten as a property of that
> case rather than of block pooling.
>
> **Confidence:** medium. The competing effect is that a blank frame has zero variance, which
> collapses SSIM's luminance *and* contrast terms in every non-empty block — and that penalty
> grows with density, working against the blank frame in exactly the dense regime.

> **Prediction 19.** At **GBA scale and realistic density** — 240×160, d ≥ 0.25, a single
> displaced sprite-sized region, so φ small — **the blank frame loses under pixel proportion,
> SSIM and GMSD alike.**
>
> **If this holds, §4.6's practical relevance to GBA Eval is materially reduced, and the write-up
> and the public page must say so in those words.** The finding would then be a statement about
> whole-content displacement on sparse displays, not about their grader's operating regime. That
> consequence is registered here, before the run, so that it cannot be renegotiated afterwards.
>
> **Confidence:** high that the blank frame loses; the registered risk is to the *framing*, not to
> the arithmetic.

**Required of the implementation.** The five strategies in `strategies.py` are hardcoded to 64×32.
The dimension-general versions this study needs are new code, and new code is a new place for a
defect — incident pattern C. So they ship with an **equivalence test**: on the real ROM A, B and C
frames the array versions must agree with `strategies.py` to within 1e-12, or the study does not
run. Frames are generated from a fixed seed and the generator is committed.

---

# AMENDMENT 9 — the two remaining quirks (2026-09-17)

Written before ROM D and ROM E exist.

`Quirks` has five fields. Three have ROMs: `shift_uses_vy` (A), `memory_increments_i` (B),
`sprites_wrap` (C). Two do not, and both are registered here so the coverage gap §7 names is
closed rather than described:

**ROM D — `jump.ch8`, the `BNNN` quirk.** The COSMAC VIP reads `BNNN` as "jump to NNN + V0";
CHIP-48 reads it as "jump to NNN + VX", where X is the high nibble of NNN. Set `V0` and `V3` to
different values and jump via `B3NN`: the two conventions land on different instructions, each
drawing the glyph at a different x. That is a **second instance of relocation** — the kind ROM A
covers — and it is registered precisely because §7 admits to one quirk per kind.

> **Prediction 20.** ROM D behaves like ROM A, not like B or C: with the glyph displaced far
> enough to touch two blocks, **no strategy separates**, and SSIM scores the correct divergent
> frame below the blank screen. Relocation is a property of the *geometry*, so a different quirk
> producing the same geometry must produce the same failure.
>
> **Falsified if** any strategy separates on ROM D, or SSIM scores its divergence above the blank
> screen. That would mean ROM A's result depends on the shift quirk specifically rather than on
> relocation, and the mechanism is wrong.
>
> **Confidence:** high. This is the prediction most likely to be called trivial, and it is worth
> registering anyway: if it fails, §4.6's central claim fails with it.

**ROM E — `vfreset.ch8`, the `8XY1/2/3` VF-reset quirk.** The VIP clears `VF` as a side effect of
the logical ops; CHIP-48 leaves it alone. `VF` is a register, not a pixel, so the ROM must make it
visible: set `VF` non-zero, run `8XY1`, then use `VF` as the *digit index* for the glyph. The two
conventions therefore draw **different digits in the same place** — the same geometry as ROM B.

> **Prediction 21.** ROM E behaves like ROM B: **pixel proportion and SSIM separate**, and SSIM
> scores the divergence above the blank screen. A second instance of substitution should replicate
> substitution's outcome.
>
> **Falsified if** ROM E fails to separate under both, which would mean ROM B's result depends on
> the index quirk rather than on the geometry.
>
> **Confidence:** medium-high. The risk is digit choice: two digits sharing most of their lit
> pixels give a much smaller divergence than ROM B's `3` vs `0`, so the acceptance gates must
> record which digits the two conventions actually reach rather than assuming.

Both ROMs must pass the same four Amendment 3 gates before any strategy runs, and on both the
population must genuinely split — a ROM every interpreter agrees on tests nothing and is reported
as inert, not tuned until it splits.

---

# AMENDMENT 10 — the corrected boundary, and an out-of-sample test of it (2026-09-17)

**Amendment 8's derivation was wrong, and this records the correction before any new run.**

Prediction 17 claimed the boundary was `φ > 0.5`, "independent of density", with the note that
this was "arithmetic, not an empirical guess" and confidence **high**. It was not arithmetic. It
dropped the collision term: content that moves does not always land on dark pixels, and at high
density most of it lands on pixels that were already lit, so the divergence produces *fewer*
differing pixels than `2φdN`. Keeping the term:

    reference lit set        |R| = d·N
    vacated, not re-lit      φ·d·N·(1−d)
    arrived on dark pixels   φ·d·N·(1−d)
    displacement error       ≈ 2·φ·d·N·(1−d)
    blank error              d·N

    blank wins  ⟺  d·N < 2·φ·d·N·(1−d)  ⟺  **φ·(1−d) > ½**

Density does not cancel. It only appeared to because the term is negligible at §4.6's
`d = 14/2048 = 0.0068` and dominant anywhere near half-lit. Both earlier claims are slices of this
one surface: at `φ=1` it gives `d < 0.5`, and as `d → 0` it gives `φ > 0.5`. The boundary curve is

    φ* = 1 / (2·(1−d))        leaving the unit square at d = 0.5

**Prediction 17 is falsified as registered** — §4.7 records it that way, and the error is logged
as an incident, because a derivation registered as certain and reported at high confidence was
wrong in a way review caught and I did not.

**The curve fits the Amendment 8 grid at all eight cells** within its 0.10 resolution, and the
flat `φ=0.5` version is ruled out at `d=0.25`, where 0.70 was observed and 0.50 predicted. That is
a **post-hoc fit**: the correction arrived after those numbers existed. It gets no predictive
credit here, and the point of this amendment is to give it a chance to earn some.

> **Prediction 22 — out of sample.** At densities not yet run, `d ∈ {0.15, 0.30, 0.35, 0.45}`,
> swept on a 0.02 grid in φ, pixel proportion's crossover lands within **±0.04** of `1/(2(1−d))`:
>
>     d = 0.15 → 0.588      d = 0.30 → 0.714
>     d = 0.35 → 0.769      d = 0.45 → 0.909
>
> **Falsified if** any of the four misses by more than 0.04, or if the observed crossovers are
> better described by a constant than by the curve.
>
> **Confidence:** medium-high, and deliberately lower than Amendment 8's. The known deviation is
> that this generator moves a *contiguous column band*, so arriving content mostly lands on the
> band's own vacated territory and collides only in a narrow leading strip — collisions there are
> roughly independent of φ rather than proportional to it, which the random-landing model assumes.
> If the curve still tracks, it tracks despite that; if it fails, this is the reason to check first.

**The SSIM boundary is a different quantity and must not inherit this curve.** SSIM pools over
blocks, so it never sees global density — it sees *block occupancy*. A blank frame disturbs every
block holding content, call it `B`; a displacement disturbs `B_vacated + B_arrived`, which at
`φ=1` with no block-level overlap is `2B`. That is exactly why §4.6's displacement sweep is flat:
4 pixels and 24 pixels both score 0.9375 because both land outside the source block.

> **Prediction 23.** SSIM's behaviour is controlled by **block occupancy, not global density**. Two
> frames with the *same* lit-pixel count — one concentrated in few blocks, one spread over many —
> will give pixel proportion the **same** blank-wins verdict and SSIM **different** ones, with the
> concentrated frame the one where the blank cheat wins.
>
> **Falsified if** SSIM's verdicts agree across the two layouts, or if pixel proportion's disagree.
>
> **Confidence:** medium. This is the sharper SSIM test and it replaces Prediction 18, which was
> falsified for asking the wrong question: it compared SSIM's crossover *in φ* against pixel
> proportion's, when φ is not SSIM's controlling parameter at all.

**One degeneracy to state rather than let a reviewer find.** A blank frame has zero variance, so
in every block SSIM's luminance and contrast terms are dominated by the stabilising constants
`C₁ = 0.0001` and `C₂ = 0.0009` rather than by any similarity judgement. The blank cheat's SSIM is
therefore partly an artefact of those constants. This does not affect whether a grader would
accept it — a number is a number, and that is the point — but any claim about *why* it scores what
it does has to say so.

---

# OUTCOMES — Amendment 9 (2026-09-17)

Both ROMs were built to the registered designs and pass all four Amendment 3 gates.

| | ROM D — `jump.ch8` | ROM E — `vfreset.ch8` |
| --- | --- | --- |
| quirk | `BNNN` jump offset | `8XY1/2/3` VF reset |
| bytes | 26 | 20 |
| reference frame | glyph at x=4 | glyph `0` at (0,0) |
| divergent frame | glyph at x=16 | glyph `3` at (0,0) |
| kind | relocation, 2 blocks | substitution, 1 block |
| gates 1–4 | all PASS | all PASS |

**Prediction 20 holds.** ROM D reproduces ROM A exactly — pixel proportion 0.9863, GMSD 0.8219,
SSIM 0.9375 against a blank screen's 0.9932 / 0.8730 / 0.9688, and **no strategy separates**. A
different quirk producing the same geometry produces the same failure, which is what the
prediction was for: had it separated, §4.6's mechanism would have been wrong.

**Prediction 21 holds.** ROM E reproduces ROM B — pixel proportion 0.9980 and SSIM 0.9943, both
above the blank screen, both separating. Substitution is scored correctly regardless of which
quirk produces it.

**And both ROMs are inert as population tests, which Amendment 9 required be reported.** All seven
interpreters produce the *same* frame on each: every one of them implements the VIP reading of
`BNNN` and of VF reset. The divergent frame in both tables therefore comes from my own
quirk-configured harness, not from any third-party interpreter. So ROM D and ROM E test the
**mechanism** — geometry predicts outcome — and say nothing about a real population disagreement,
unlike ROMs A, B and C, where the population genuinely split.

That is itself a small finding worth recording: of the five documented quirks, this population
varies on **three** (`shift_uses_vy`, `memory_increments_i`, `sprites_wrap`) and is unanimous on
**two** (`jump_uses_vx`, `vf_reset`). The quirks that divide real implementations are a subset of
the quirks that divide the documentation.

**A gate that did not check what it said.** Amendment 9 wrote "the population must genuinely
split — a ROM every interpreter agrees on tests nothing" as a requirement, and `check()` never
tested it: gate 4 only asks whether at least two third parties reproduced *either* expected frame,
which a unanimous population satisfies. Both ROMs passed all four gates while testing nothing
about the population. `Acceptance.population_splits` is now reported as **gate 5**, and it fails
for ROM D and ROM E. It is reported rather than folded into `accepted`, because it is a fact about
the population rather than about whether the ROM is well-formed.

This is another instance of the pattern in §2 — a requirement written in prose, believed to be
enforced, and inert — and it is logged there.
