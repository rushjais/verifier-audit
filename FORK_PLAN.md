# FORK_PLAN.md — MVP

~3–4 weeks at **~10 live hrs/week**, plus offline run time. Everything cut is in §9 (v2), not
deleted. Read `CLAUDE.md` §"The one protected invariant" before touching anything that grades.

---

## 0. The goal

The original proves one narrow thing: a standard EvalPlus grader can be breached by harness
tampering and sealed by grading from a pristine copy.

**What this adds:** the original audits graders in ONE direction — *can this be cheated?* The
production pain is both directions: a grader must reject cheats **and** accept honest work **and**
return the same verdict twice. The second half is done by hand today, one property at a time
(SWE-bench Verified used human annotators for it). Automating it per grader is the MVP.

## 0b. Two budgets, tracked separately

The reason this fits in 10 hrs/week:

| | what it is | the constraint |
| --- | --- | --- |
| **Attention hours** | writing/reading code, judging output, deciding | ~10/week — the scarce one |
| **Offline hours** | agent transcripts, k×m grader reruns, generation sweeps | wall-clock, kick off and walk away |
| **Dollars** | API spend on the above | hard cap per milestone, §3 |

Design bias: anything that can be moved from attention to offline, move it. The auditor is
deliberately shaped this way — a long, dumb, expensive run producing a small table you read once.

---

## 1. Weaknesses being fixed (MVP only)

| weakness in the hackathon result | fixed by |
| --- | --- |
| `honest_pass` measured against **one** gold solution, not a population | M1 (4a) |
| Determinism asserted, never measured | M1 (4b) |
| `RedResult` keeps only the last text block — no transcripts, no failure analysis | M0 |
| Procedural graders only; no LLM-rubric grading | M2 |
| One cheat family (harness tamper) | M2 adds one more: `judge_injection` |
| HumanEval only — no task with a real specification gap | M1b (one task) |

Not fixed in MVP, and honestly labeled as such: the other seven cheat families, four task shapes,
rubric hardening templates, and the substrate generalization. See §9.

---

## 2. Branch, not fork (yet)

**Work on a branch in the existing repo.** No fork, no split, nothing public. This removes the
teammate conversation from the critical path entirely.

Asked and answered: they were happy for this to continue solo, and asked that it live in a
separate repo so the original stays theirs. Hence this repo, with the full history preserved and
attribution in the README.

Attribution block, written at that point, not now: original 2-day hackathon Jun 20–21 2026 by
Advay Monga, rayan-arya, and you; yours was track C (event bus, siege dashboard, `viz3d`,
leaderboard frontend); everything after `<date>` in `audit/` and `grader/rubric.py` is solo.

---

## 3. Milestones

Dollar figures are **estimates with a hard cap** — stop the run at the cap and report what you
have rather than continuing. Set the cap in the Anthropic console before M1.

| | what | attention | offline | $ cap |
| --- | --- | --- | --- | --- |
| **M0** | Transcript capture in `red.py` | ~4 h | — | $0 |
| **M1a** | Auditor 4a + 4b + 4e on stock *and hardened* EvalPlus graders | ~11 h | ~6 h | **$40** |
| **M1b** | One replication task + 4c on it (hardcoded, no protocol) | ~7 h | ~1 h | $10 |
| **M1c** | CHIP-8 differential-grading study (§6b) — the centerpiece | ~10 h | ~2 h | **$1** |
| **M3** | `GraderReport` + failure writeup + README | ~8 h | ~3 h | **$25** |

~40 attention hours (4+11+7+10+8). Total cap **$76**.

M2 (rubric grader + `judge_injection`) moved to v2 — M1c replaces it as the centerpiece rather
than adding to it. That also removes the single most expensive milestone.

**Sequencing rule:** M0 first because everything downstream reads transcripts. M1a before M1b —
get real numbers out of the substrate that already works before building a new one.

---

## 4. M0 — Transcript capture

`RedResult` currently keeps `notes`: the last text block the model emitted. That is not enough to
say anything about why a model failed, and it blocks M3 entirely.

Capture per run, to `runs/transcripts/<task_id>__<run_id>.jsonl`: every message, every tool call
and result, timestamps, token counts, final R and T, model, and the specialist/cheat_type if any.

Keep it small and injectable — tests must still run with no disk and no network.

## 5. M1a — The fairness auditor (the centerpiece)

New package `src/rampart/audit/`. Four checks, two of them free.

**4a — Honest-solution coverage.** Generate k=20 *diverse* honest solutions per task (vary model,
prompt, and idiom — recursive vs iterative, stdlib vs hand-rolled). Every rejection is a fairness
bug and ships with a repro.

    honest_pass = accepted / |{s in proposed : oracle(s) = 1}|

The denominator is load-bearing: a proposal joins the population only after the oracle confirms
it correct, or a rejection is ambiguous and the rate means nothing.

**Measure it on HARDENED graders, not stock ones.** On unpatched EvalPlus the grader is the base
HumanEval suite and the oracle is the stricter extended suite, so anything the oracle accepts the
base grader accepts too — honest_pass is ~1.0 by construction and 4a finds nothing. The real
question is whether *hardening* over-tightens. The original loop patches graders to seal cheats
and never checked what those patches cost in legitimate work, so the headline is the honest-pass
**delta from grader to grader'** — the collateral damage of sealing.

Three things that make the number honest, all from review:
- **Measure diversity, don't assume it.** LLM-generated solutions converge; report how structurally
  distinct the k actually are, and prompt for deliberately different approaches.
- **Counts beside rates.** At k=20 one rejection is 5%. Pool across tasks where it is valid to.
- **The oracle can be wrong too** (exact float formatting). Hand-check every oracle/grader
  disagreement before calling it a grader failure.

**4e — Mutation catch rate.** The sibling of 4a and the same shape:

    catch_rate = rejected / |{m in mutants : oracle(m) = 0}|

Single-point AST mutations of the reference (comparison swaps, arithmetic swaps, boolean swaps,
constant bumps), differentially filtered so only genuinely broken mutants count — a mutant the
oracle still accepts is behaviourally equivalent, and accepting it is not a grader failure.

Together 4a and 4e are the grader's sensitivity and specificity against the oracle. Either is
trivially maxed alone, so neither is ever reported without the other. And because mutants are
generated by AST surgery, this column is deterministic, reproducible, and **costs $0** — it is
what makes "how strong is this grader" affordable without red-agent runs.

Escaped mutants — real bugs the grader cannot see — are the useful artifact.

**4b — Determinism.** Run the grader m=10 times over a fixed submission set. Flag every unstable
verdict and attribute it: procedural (timeouts, iteration order, unseeded randomness, wall-clock)
vs rubric (LLM drift at fixed temperature). Report `flake_rate` per component.

**4b′ — Harness-path.** Record what the grader is called with — arguments, config, environment —
in its own test harness and in a real rollout, then diff them. See §11 story 1: this is the defect
that survives every other check. Ships as **a small instrumentation helper plus a checklist,
demonstrated on one or two graders. It is not billed as generic** — the generic version is
line-level coverage comparison, which is v2.

**4c (unknowability) is an MVP pilot on the M1b task only, and that is a substrate fact, not a
dodge.** HumanEval prompts are docstrings with worked examples; the specification gap is near zero
by construction, so 4c there would find nothing and the null would be an artifact of the
substrate. The replication task in M1b has a real gap by design. An LLM lists the grader's
assertions and checks each against the prompt; **the results are hand-verified and the whole thing
is labelled a pilot.** Building a spec gap into your own task to test the auditor does not
violate discover-don't-plant — nothing is being handed to an agent; the auditor is what is under
test.

4a, 4b and 4e are cheap in attention and expensive in wall-clock. Run them overnight.

## 6. M1b — One replication task

One. Hardcoded, its own module, **no protocol, no abstraction, no refactor** — a second substrate
is what would justify a `Substrate` interface, and one does not.

**Shape: replication, not bug-fixing.** A short spec describes a small pure-Python module; a
reference implementation exists but is never shown to the agent; the grader is a differential
test — does the candidate behave identically to the reference? This is the paradigm Mechanize's
["GPT-3 moment for RL"](https://www.mechanize.work/blog/the-upcoming-gpt-3-moment-for-rl/) argues
the field will run on, and the same essay concedes "writing effective and comprehensive tests
remains a non-trivial task."

Why this shape rather than a planted bug:

1. **Its fairness failure is notorious and measurable.** Differential graders reject
   behaviourally-equivalent implementations over incidental differences — dict iteration order,
   error-message text, float formatting, which exception type, internal API shape. That is
   honest-pass failure in its purest form, and 4a measures it directly.
2. **It supplies a real specification gap**, so 4c comes back into the MVP: the spec says what to
   build, the grader tests behaviour, and everything the grader asserts that the spec never made
   derivable is an unfair assertion.
3. **The reference implementation is a free oracle** — correctness of a candidate is decided by
   behavioural equivalence on held-out inputs the grader never uses.
4. **Mutation testing drops straight in** — mutate the reference to generate buggy variants, and
   the fraction the grader catches is a deterministic, zero-API-cost measure of grader strength
   (the trick TestBench-Forge used at the same hackathon).

**Invariant:** the reference and the held-out equivalence inputs are never materialized in the
workdir; grader and oracle share zero cases. Explicit test.

## 6b. M1c — a CHIP-8 differential-grading study (the centerpiece)

**Why.** Mechanize published [gbaeval.com](https://gbaeval.com): frontier agents get 24 hours to
write a GBA emulator, graded against Mesen2 via SSIM, log-mel spectrogram distance, and procedural
test ROMs. Stephen Yang's [grading-iteration post](https://gbaeval.com/blog/grading-iteration)
defines fairness as:

> it should be possible to get a perfect score on the eval, and
> the ranking implied by the grading strategy over the space of all possible emulator
> implementations should be highly correlated with human judgement

That is `honest_pass = 1.0`, then `honest_pass` generalised over a population of correct
implementations. The post is five attempts, and each failure is a fairness or catch failure of a
differential grader against a reference — exact frame match scores functionally perfect emulators
near zero; proportion-of-pixels gives a blank white screen 99% while scoring a one-channel palette
shift at 0; a global threshold cannot be fair on a flashing intro and discriminating on a calm
scene; GMSD scores a visually indistinguishable emulator near zero.

**We are not claiming we would have saved them that work.** They found those dead ends quickly by
looking at frames. The contribution is turning grading-strategy choice into numbers, and letting
the table speak.

### Domain: CHIP-8

Tiny, deterministic, framebuffer output — a GBA Eval in miniature. Critically, independently
written CHIP-8 interpreters **genuinely disagree** on documented quirks (`8XY6`/`8XYE` shift
source, `FX55`/`FX65` index increment, `BNNN` jump offset, sprite wrapping, VF reset on
AND/OR/XOR). Both sides of each quirk are defensible. That is honest variation that nobody
planted — which is the entire reason to use real implementations rather than ones we write.

### The population, and the rule that keeps it honest

- **Correct implementations: third-party, independently written, not ours.** Fetched by pinned
  commit from a manifest — never vendored — so the repo stays licence-clean and publishable. Each
  entry records URL, commit, licence, and its known quirk settings.
- **Cheat submissions: ours, and obviously so.** Blank screen, frozen first frame, wrong palette,
  correct-but-one-frame-late. These are the catch-rate population.
- **Reference:** one implementation designated as the Mesen2 analogue.

**Pre-registration.** `PREDICTIONS.md` is written and committed BEFORE any strategy is run, with
a prediction per strategy per metric and a one-line rationale. Hits and misses both get reported.
Without this, whoever writes both the population and the metrics can produce any result they like
— the M1b fixture is the cautionary example, and it was ours.

### The table

```
strategy               honest_pass (k real impls)   catch_rate (cheat submissions)
exact match                     x/k                          y/c
pixel proportion                x/k                          y/c
thresholded (tau=..)            x/k                          y/c
GMSD                            x/k                          y/c
SSIM                            x/k                          y/c
```

Both numbers for every strategy, always, with counts beside rates.

**Stretch, free, and possibly the best result in the project: rotate the reference.** Designate
each correct implementation as the reference in turn and recompute. If `honest_pass` under exact
match swings depending on which correct implementation you happened to pick, that is a direct
measurement of how arbitrary differential grading is — and it needs no new machinery.

**Reuse:** `measure_honest_pass`, `measure_catch_rate`, `isolation`. New work is the ROM harness,
the manifest, and the five metrics.

**Estimate:** ~10 attention hours, ~2 h wall-clock, **~$1** (population generation only if we need
synthetic variants at all; the real implementations are free). Licences checked per entry before
use.

**The honest limit.** This demonstrates a known phenomenon on a small console, not a discovery.
Its value is that grading-strategy choice becomes a measurement instead of a judgement call.

---

## 8. M3 — Report and writeup

**`GraderReport`** — one page per grader, and this page is the artifact:

```
task        grader       exploitable       fair            deterministic   harness-path
────────────────────────────────────────────────────────────────────────────────────────
<id>        procedural   catch 0.42→1.00   honest 19/20    flake 0/10      ok
<id>        rubric       catch 0.10→0.80   honest 20/20    flake 3/10      MISMATCH
```

**The writeup** — why frontier models fail, over N sampled transcripts, with quoted evidence and
rates. Hard line between *model lacked a capability* and *grader was unfair*: a model scoring zero
because the grader was wrong is an M1 finding, not a capability finding. Keeping that line clean is
most of the document's value.

Write it in an engineering-log voice — dated amendments that overturn earlier claims, an
explicit rejected-hypotheses section, a population predicate on every number.

---

## 9. v2 — cut, not deleted

Revisit after fall break, and only if there's a reason to:

- `Substrate` protocol refactor — only pays off with a second substrate; one hardcoded task
  doesn't need it, and cutting the four task shapes makes the refactor pointless. They live or
  die together.
- The other three task shapes (convention-judged feature add, refactor with differential oracle,
  open-ended QA)
- The other seven cheat families (`special_case_inputs`, `swallow_exceptions`,
  `mutate_global_state`, `side_channel`, `resource_abuse`, `spec_lawyering`, and the two that
  already exist generalized)
- Rubric hardening templates (submission quarantine, instruction hierarchy, diff-only view,
  k-vote majority)
- 4c at scale, 4d (divergent interpretation)
- **M2: the LLM-rubric grader and the `judge_injection` cheat family.** Was the MVP centerpiece;
  displaced by M1c, which is cheaper, free of API spend, and aimed at a problem Mechanize has
  published about. `judge_injection` remains an untested hypothesis and is labelled as one.
- Public fork, scrubbed writeup, website

---

## 10. Anti-theater commitments

Carried from `SPEC.md` §3b. These are the reason anyone should believe the numbers.

1. **Discover, don't plant.** `SEED_LIST == []`, mechanically tested — add a test asserting no
   discovered exploit's text appears in any specialist prompt.
2. **The oracle is never materialized** in the agent's workdir. Per-task test.
3. **Held-out split is sacred.** Patch on train, measure on held-out.
4. **Every robustness number ships with `honest_pass` beside it.**
5. **Every fairness finding ships with a runnable repro.**
6. **Every number states its population**: `count = … where <predicate>`. Your own standing rule
   carried over from a production system I maintain, adopted after several miscount incidents.
7. **Report the failures.** Families with a zero hit rate, graders you couldn't harden, tasks
   dropped and why. And keep a rejected-hypotheses list.
8. **No claim before a run.** Judge injection is a hypothesis until measured (§7).

---

## 11. Positioning and outreach

Kept out of the repo deliberately — see `POSITIONING.md`, which is gitignored. It holds the
career framing and positioning notes. None of that is technical content
and none of it belongs in a public repository.
