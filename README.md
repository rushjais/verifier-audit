# vaudit

**An instrument for auditing graders, and a record of it failing at its own job sixteen times.**

The tooling measures whether a grader accepts correct work, agrees with itself, and tests only
what it told the candidate. It works. Everything it measured turned out to replicate established
results — `LITERATURE.md` is unsparing about that.

What the project produced that is not a replication is `WRITEUP.md` §2: sixteen occasions inside
one small project where a measurement was confidently about something other than what it claimed,
each with a traced cause, none caught by the thing that broke. Four patterns, each with a direct
analogue in building RL graders. Start there.

A verifier used for RL or evaluation has to do three things: reject every cheat, accept every
legitimate solution, and return the same verdict twice. Tooling exists for the first. This
measures the other two.

```
4a  honest_pass  = accepted / |{s : oracle(s) = 1}|      correct work the grader accepts
4e  catch_rate   = rejected / |{m : oracle(m) = 0}|      broken work the grader rejects
4b  flake_rate   = unstable / |{submissions x m runs}|   verdicts that change on rerun
4b-prime         does the grader's own harness exercise what the rollout exercises?
4c               what does the grader assert that the prompt never made derivable?
```

`4a` and `4e` are deliberately the same shape — sensitivity and specificity against the oracle.
Either is trivially maxed alone (accept everything, reject everything), so neither is ever
reported without the other beside it. Every number carries the population it was computed over.

None of these is a new idea. Screening a benchmark for over-specific tests is what human
annotators did for SWE-bench Verified; flaky-test detection is an established field. What does
not exist is the automated, per-grader combination, reported repeatably as a grader changes.

## Results so far

**Scope note.** The numbers below describe *this sample*: seven Python CHIP-8 interpreters found
by GitHub search, permissively licensed and adaptable to a headless harness. They are not a random
sample of interpreters, not a claim about interpreters in other languages, and not an estimate of
any misgrading rate in the wild.


- **EvalPlus base graders miss 25–38% of genuinely broken mutants** on two of five of the
  hardest tasks — deterministic, no API spend.
- **A differential grader rejected 5 of 6 spec-faithful implementations** of a small replication
  task, every rejection tracing to something the spec never determined (record type, summary
  type, exception type, float precision). Labelled a pilot: the spec gap is authored, because
  the auditor is what is under test.
- **Null result, reported:** hardening cost nothing in legitimate work across 5 EvalPlus tasks.
  Recorded rather than dropped.
- **One of seven** interpreters in this sample passes the reference correctness suite
  (`Timendus/chip8-test-suite`). Four of the six failures are traced to specific lines in their
  own source (`ADAPTERS.md`); two are untraced and marked as such. What this supports is narrow:
  *when picking a reference implementation for differential grading, correctness cannot be
  assumed from the fact that something is a working, published interpreter.* It is not a rate.

## Run it

```bash
uv sync
python -m vaudit.tasks.chip8.fetch      # population + ROMs at pinned commits
make check                              # 155 tests, offline, no API key
python -m vaudit.audit.sweep --tasks 5  # prices a run; buys nothing without --confirm
```

Run `make check` before fetching and you get 111 passed, 14 skipped: the adapter tests skip
cleanly when the population is absent, so the suite can never pass while silently claiming a
study that did not run.

## Origin

This began as my solo continuation of **Goodhart**, a two-day project from the HUD Frontier / RSI
RL Environments hackathon (20–21 June 2026) built with [Advay Monga](https://github.com/advaymonga)
and [rayan-arya](https://github.com/rayan-arya), which placed 9th of 71. My contribution there was
the event bus, dashboard, and leaderboard frontend — not the verifier core.

This repository shares no code with it. The sandbox, substrate loader, grader, and oracle are
written from scratch here (and the sandbox drops the test-framework dependency the original had,
which made every sandboxed run roughly ten times cheaper). Everything in `audit/`, `isolation.py`,
and `tasks/` is mine. The original remains with its authors.

One finding did come out of that work and is worth recording: the original sealed harness
tampering by rebuilding its test suite from the task, but a candidate could still read the
expected values out of the generated module's namespace. `isolation.py` closes that by putting a
process boundary between the candidate and the answers — the child receives only the inputs.
