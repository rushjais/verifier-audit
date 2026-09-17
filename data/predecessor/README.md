# Predecessor-repository artifacts

These were produced by the **predecessor repository**, before the clean-room rewrite, by code that
is **not in this repository**. They are archived here so the one result that cannot be regenerated
still has an artifact behind it rather than only a sentence.

## `m1a_sweep.json`

The run behind WRITEUP §4.2 (the hardening null). Its `honest_pass_stock` and
`honest_pass_hardened` columns are 1.0 on all five tasks — delta 0.00.

The hardening track was dropped in the clean-room rewrite: its patch template was my former
teammates' code, and re-adding a hardening step of my own would make the null close to
tautological, since hardening with cases derived from the reference cannot reject a correct
solution. So this file is evidence of what was measured, not something this repository can
reproduce. Treat it accordingly.

Its `catch_rate_stock` column (0.625, 1.0, 1.0, 0.75, 1.0) is the predecessor half of the
comparison table in §4.1, and *that* half did reproduce here exactly.
