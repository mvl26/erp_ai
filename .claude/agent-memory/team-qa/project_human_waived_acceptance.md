---
name: human-waived-acceptance
description: How to close acceptance.md when the human accepts despite qa rework (FEAT-004 2026-11-14) — verdict-line regex pitfalls
metadata:
  type: project
---

FEAT-004 (2026-11-14): human chose "Chấp nhận với bằng chứng hiện có" over qa's `rework`. qa kept its own verdict as a section ("Phán quyết riêng của qa", no colon after the word), added "Đã đóng", "Quyết định của người", "Còn mở" (O-1..O-24, mirrored in debt.md), then a plain-text warning line and a final exact `Verdict: accepted`.

**Why:** team.py uses `re.search` (first match) for `(verdict|phán quyết)\**\s*:\**\s*(accepted|rework|design-defect)`; an old `Verdict: rework` or `Phán quyết: rework` left anywhere earlier wins over the last line. The verify skill also greps `^Verdict: (…)$`, so no trailing words on the line.

**How to apply:** on any waived/forced acceptance, reword earlier verdict mentions so no colon follows "Verdict"/"Phán quyết", put the "not a clean qa pass" wording on the line above, then check with `grep -niE '(verdict|phán quyết)\**\s*:'` (exactly one hit) and `team.py status`. See [[post-handover-manual-steps]].

Applied again to CHG-001 (2026-11-15, "Chấp nhận như FEAT-004"). Pitfall seen: team.py's `released` regex `Released\**\s*:\s*\S` lets `\s*` cross newlines, so an EMPTY `Released:` header in asbuilt.md (writer, in parallel) makes status jump to `released`, hiding `verified`. Report it to team-leader; qa cannot edit asbuilt.md.
