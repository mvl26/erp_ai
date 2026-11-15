---
name: redact-rulings-regress
description: FEAT-007 redact.py design rulings have twice shipped a regression (leak / super-linear cut); always probe leaks and scaling against the previous commit
metadata:
  type: project
---

2026-11-15: in two rounds of the T174 review, the ruled code for `erp_ai/agent/redact.py` (K-7 tail in round 1, K-4b cut in round 2) was implemented exactly as written, and it still caused a regression. Round 1 leaked the next key's value. Round 2 made the scan O(n^2) on `"pwd=a|"*N` (240 KB took 16 s) and exposed text after a secret key that has no value (`password=abc|api_key:,hunter2`).

**Why:** the designer's case table only covers the cases it lists. Doubling-N timing and "secret key with an empty value inside a secret value" were never measured.

**How to apply:** when you review any redact.py change, run the three versions (base, previous, head) with `exec` on `git show` text. Time each input at N, 2N and 4N. A 4x jump per doubling of N means quadratic. Probe `,;&` right after an inner secret key. Dev followed the ruled code, so this kind of result is a `design-defect`.
