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
