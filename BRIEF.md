# BRIEF, what this project is, for a reviewer

Hand this to another agent or person and ask them to pressure-test it. Self-contained;
`FORK_PLAN.md` is the execution detail, `SPEC.md` is the hackathon original.

---

## One paragraph

RL environments are graded by verifiers. A verifier is only useful if it is **un-gameable,
fair, and deterministic**. It must reject every cheat, accept every legitimate solution, and
return the same verdict twice. This repo started as a 2-day hackathon project (Goodhart) that
attacked the first property only: find cheats in a grader, patch them, report the improvement.
**The solo continuation attacks the second and third**, which today are handled by hand or
one property at a time. The
deliverable is a one-page audit report per grader plus a written analysis of why frontier models
fail at the tasks, derived from sampled transcripts.

## Why the second half is the open lane

The HUD Frontier / RSI RL Environments hackathon ran 71 projects. At least six attacked
verifier exploitability:

| project | placement | what it does |
| --- | --- | --- |
| Traceback | #6, Best Design | Snapshot an agent trajectory at a forkpoint, fan parallel attackers out from it, auto-patch the verifier, prove the fix |
| **Goodhart (ours)** | **#9** | Red swarm finds cheats in a grader; green team hardens it; report before→after |
| TestBench-Forge |, | "Train the grader, not the answer" |
| Protean |, | Non-gameable, root-owned verifier for Triton kernels |
| LoopHole |, | "Every agent loop has a hole. We find it." |
| SAE Heist |, | Can an RL agent game SAE Bench without improving interpretability? |

**Exploitability is crowded and Traceback did it better than we did**, real substrate
(Terminal Bench 2.1), Modal snapshots so multi-step hacks are reachable, 14 confirmed deduped
hacks, and a three-part release gate. Rebuilding that is a losing move.

**What none of them measure is whether the grader is fair to honest work.** Traceback comes
closest and its check is *three hand-authored control fixtures* used as a release gate
(`src/forkproof/controls/`, `if len(controls) != 3`).

**The honest version of the novelty claim**, because the naive one does not survive contact with
prior work: screening a benchmark for over-specific tests and underspecified problem statements
is exactly what human annotators did when OpenAI built SWE-bench Verified, 4a and 4c, by hand,
once. Flaky-test detection is a large established field in software engineering, and LLM-judge
consistency is widely studied. None of this is a new *idea*.

What does not exist is the **combination, automated and per-grader**: one command that reports
fairness beside robustness for a specific verifier, repeatably, as it changes. And the SWE-bench
Verified precedent cuts in our favour on value even as it cuts against novelty, the current
state of the art being expensive one-shot human annotation is the argument for automating it.
That search has now been done, see `LITERATURE.md`. It found substantial prior art for every
check, including the one §4.6 rests on, and the claims above are weaker than they read. Read the
literature review before quoting anything from this document.

## The same argument in the field's own economics

Mechanize's ["Cheap RL tasks will waste compute"](https://www.mechanize.work/blog/cheap-rl-tasks-will-waste-compute/)
argues labs should spend thousands of dollars of engineering per task because compute is
~$2,400 per task, "putting cheap tires on a Ferrari." Run that argument one level down:

**An unfair grader does not merely fail to help. It spends the most expensive resource in the
pipeline teaching the model that correct behavior is wrong.** If a grader rejects 15% of
legitimate solutions, 15% of that compute produces actively harmful gradient, not zero gradient.
A flaky grader is worse still: it injects noise straight into the reward signal.

Nobody measures either number today. That is what this produces.

Two more of their positions bear directly on the design:

- ["The upcoming GPT-3 moment for RL"](https://www.mechanize.work/blog/the-upcoming-gpt-3-moment-for-rl/)
  proposes **replication training** as the flagship paradigm, duplicate a reference
  implementation from a spec, graded by "either the generated implementation behaves identically
  to the reference, or it doesn't", and concedes in the same breath that "writing effective and
  comprehensive tests remains a non-trivial task."
- ["How to fully automate software engineering"](https://www.mechanize.work/blog/how-to-fully-automate-software-engineering/)
  names what they cannot currently grade: open-ended instructions from customers without a full
  technical specification, maintainability and technical debt, and trapdoor decisions.
  "Designing tasks for RL requires figuring out how to automatically grade model performance."

The second list is the v2 roadmap. The first changes M1b, see below.

## The four checks

| | check | question | status |
| --- | --- | --- | --- |
| 4a | Honest-solution coverage | Of k=20 *diverse* correct solutions, how many does the grader accept? | **MVP** |
| 4b | Determinism | Over m=10 reruns, how often does the verdict change, and is it the procedural or the LLM half? | **MVP** |
| 4b′ | Harness-path | Does the grader's own test harness exercise the code path the real rollout does? | **MVP** |
| 4c | Unknowability | What does the grader assert that the prompt never made derivable? | **MVP, as a hand-verified pilot** on the M1b replication task |
| 4e | Mutation catch rate | Of mutants the oracle confirms are broken, how many does the grader reject? | **MVP**, deterministic, $0, no red-agent runs |

4a and 4e are deliberately the same shape, of solutions the oracle calls CORRECT, how many does
the grader accept; of mutants the oracle calls BROKEN, how many does it reject. Sensitivity and
specificity against the oracle. Either is trivially maxed alone (accept everything, reject
everything), so neither is reported without the other beside it.

**Where 4a actually bites is hardened graders, not stock ones.** On unpatched EvalPlus the grader
is the base HumanEval suite and the oracle is the stricter extended suite, so anything the oracle
accepts the base grader accepts too and honest-pass is ~1.0 by construction. The real question is
whether *hardening* over-tightens: the original project's whole loop patches graders to seal
cheats, and nobody checked what those patches cost in legitimate solutions. So the headline metric
is the honest-pass **delta under hardening**, the collateral damage of sealing.

4b′ comes from a real incident in a production system of mine: an acceptance test called a
function with `top_k=100`, production sent `top_k=10`, and a feature recorded as shipped had
never once executed in production. The log line appeared zero times. Green for a reason
unrelated to the thing being measured is the failure mode this check exists to catch.

## Scope

**MVP (~40 attention hours, $150 cap):** M0 transcript capture (done) → M1a auditor 4a+4b+4b′+4e on
the existing EvalPlus graders → M1b one replication task (+4c on it) → M2 minimal LLM-rubric grader
plus a `judge_injection` cheat family → M3 report + failure write-up.

**Explicitly cut to v2:** the `Substrate` protocol refactor, three more task shapes, seven more
cheat families, rubric hardening templates, 4c at scale. Rationale in `FORK_PLAN.md` §9.

## Rules that constrain the work

1. **Discover, don't plant.** `SEED_LIST == []`, mechanically tested, no exploit is ever handed
   to an agent; agents get cheat *categories*, never answers.
2. The oracle is never materialized in the agent's workdir; grader and oracle share zero cases.
3. Patch on a train split, measure on a held-out split.
4. Every robustness number ships with honest-pass beside it.
5. Every fairness finding ships with a runnable repro.
6. Every number states its population: `count = … where <predicate>`.
7. Report the failures, zero-hit families, graders that resisted hardening, dropped tasks, and a
   maintained rejected-hypotheses list.
8. **No claim before a run.** `judge_injection` is a hypothesis, not a finding.

## What I want pressure-tested

1. Is "grader fairness" actually an unoccupied lane, or am I missing prior work? Traceback's
   3-fixture control gate is the closest thing I found.
2. Honest-pass is now measured as a *delta under hardening* rather than on stock EvalPlus, where
   it is ~1.0 by construction. Open sub-questions: LLM-generated solutions tend to look alike, so
   diversity has to be measured and reported rather than assumed; at k=20 a single rejection is
   5%, so counts go next to rates; and the oracle itself can be wrong (float formatting), so any
   oracle/grader disagreement gets hand-checked before it is called a grader bug.
3. 4b′ ships as a small instrumentation helper, record what the grader is called with in its
   own harness and in a real rollout, then diff, plus a checklist, demonstrated on one or two
   graders. It is **not** billed as generic. Is even that overclaiming?
4. M1b is now a **replication task** (build X from a spec; grade by differential test against a
   reference) rather than a repo with a planted bug. Rationale: it is the paradigm the field is
   betting on, its grader has a notorious and measurable fairness failure, rejecting
   behaviourally-equivalent implementations over incidental differences like dict ordering or
   error-message text, and it supplies the specification gap 4c needs. Is that shift right?
5. Is the MVP still too big for ~10 live hrs/week?

## Attribution

2-day hackathon original (Jun 20–21 2026) by Advay Monga, rayan-arya, and me; placed #9 of 71.
My contribution then was track C, the event bus, siege dashboard, `viz3d`, leaderboard frontend.
Full history is preserved here. Everything from `dc39351` on is solo, and the teammates asked
that this continue in a separate repo so they keep the original.
