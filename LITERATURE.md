# Prior work, the search `BRIEF.md` promised, done 2026-09-17

`BRIEF.md` said "a real literature search goes before publication, not after." This is it, and it
went badly for the novelty claims. Every check in this instrument has substantial prior art, and
the §4.6 headline rests on a documented, named, twenty-year-old property of SSIM.

Recording it in full rather than adjusting the claims quietly.

## 4a, honest-pass over a population of correct solutions

**Prior art: the automated-grading literature, and it is closer than anything else found.**

Work on autograding programming assignments has measured this directly, reporting an assessment
mechanism with **56.4%–64.1% false-negative error**, correct submissions wrongly rejected, against an improved mechanism at 0%–0.02%. It also names the mechanism §4.3 demonstrates: test
suites produce false negatives "because the problem description allows for multiple distinct
correct outputs for a given test input, but the test cases require one particular correct output
instead." Separate work on LLM-generated test suites for autograding records a single run in which
invalid generated tests failed **1,224 valid solutions**.

**Consequence.** §4.3 (a differential grader accepting 1 of 6 spec-faithful implementations) is a
**replication** of a known and much better-quantified phenomenon, on a smaller sample. It is not a
discovery, and the write-up should not have implied the fairness direction was unmeasured.

## 4e, mutation catch rate

**Prior art: mutation testing, since 1977.** `catch_rate` *is* the **mutation score**, "the ratio
of mutants killed by a test suite", a fault-based test-adequacy metric with over **390
publications catalogued between 1977 and 2009**. The differential filter that excludes
behaviourally-identical mutants is the **equivalent mutant problem**, known and NP-complete.

**Consequence.** 4e contributes nothing methodologically. Applying mutation score to an RL grader
rather than a unit-test suite is a relabelling of the same measurement.

## 4b, 4c, flakiness and unknowable assertions

Flaky-test detection is an established field, as already stated. 4c's two questions are, verbatim,
the annotation criteria OpenAI used for SWE-bench Verified with 93 developers. Both were already
credited; nothing changes.

## §4.6, SSIM ranking a blank screen above a correct implementation

**Prior art: SSIM's sensitivity to spatial translation is a documented drawback with a named
fix.** The image-quality literature states plainly that "a key drawback of both MSE and SSIM
metrics is their high sensitivity to small geometric distortions such as translation, rotation and
scaling", and that "small translations that are hardly visible significantly affect most metric
scores." **CW-SSIM** (complex-wavelet SSIM, Wang and Simoncelli, 2005) was designed specifically
to compensate for small translations and rotations.

**Consequence, and it is the largest correction here.** The §4.6 mechanism, that SSIM penalises
relocation, is textbook, not a finding. Predictions 12, 14, 15 and 16 were registered against a
mechanism that was already published; they confirm it in a new setting rather than discovering it.

## What survives

1. **The consequence, in a grading context.** That SSIM's known translation sensitivity means a
   reference-based grader ranks a correct-but-quirk-divergent implementation **below a blank
   screen** is a corollary of published facts, demonstrated rather than derived. GBA Eval selected
   SSIM after rejecting four alternatives and does not appear to note this regime; whether their
   frames sit in it is measurable and unmeasured.
2. **The automated per-grader combination.** No prior work was found that reports fairness beside
   robustness for a specific grader, repeatably, as it changes, but this was not searched
   exhaustively and the claim is weaker for that.
3. **The method.** Pre-registration with dated amendments, falsifiers stated in advance, and a
   mechanism put at risk by Predictions 14–16.
4. **§2 and Appendix A.** A first-person record of twenty measurements in one project that
   were about something other than what they claimed. Nothing found in the search resembles it, and
   on reflection it is the most original content here.

## What was not searched

No systematic search for: reward-model or LLM-judge evaluation benchmarks; metamorphic testing as
a fairness check; differential-testing metric selection outside image quality; or CS-education work
on multiple-correct-output grading beyond the results above. Any of those could reduce claim 2
further.

## Sources

- https://cs.brown.edu/people/qxin/papers/testgen_issta17.pdf, test-suite-overfitted patches
- https://link.springer.com/article/10.1007/s10664-020-09920-w, patch assessment at scale
- https://arxiv.org/pdf/2301.03270, survey of learning-based automated program repair
- https://www.cs.tufts.edu/~nr/cs257/archive/autograde-icse-2019.pdf, automatic grading of assignments
- https://arxiv.org/pdf/2411.09261, LLM-generated test suites for introductory programming
- https://twistedsquare.com/Grading-SLR.pdf, systematic review of automated grading tools
- https://arxiv.org/pdf/2212.06118, survey of oracle-based test adequacy metrics
- https://www.academia.edu/10447222/An_Analysis_and_Survey_of_the_Development_of_Mutation_Testing, mutation testing survey
- https://arxiv.org/pdf/1207.2234, equivalent mutant detection
- https://www.cns.nyu.edu/pub/eero/wang05b.pdf, CW-SSIM, translation-insensitive similarity
- https://arxiv.org/pdf/2405.08431, similarity metrics and their translation sensitivity
- https://arxiv.org/html/2408.06075v2, pitfalls in reference-metric assessment
