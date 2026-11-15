---
name: post-handover-manual-steps
description: When spec Success/DoD places manual browser steps "sau bàn giao (việc của người)", team-leader rules they do not block the build verdict (FEAT-002, FEAT-003)
metadata:
  type: project
---

If the spec's Success row and DoD say the manual (browser) steps are "sau bàn giao (việc của người)", team-leader treats them as post-handover human work. They are not `NOT VERIFIABLE` for the build verdict. This was decided for FEAT-002 AC-10/AC-11 and again for FEAT-003 J1.1–J1.7 on 2026-11-12, in decide mode.

**Why:** qa has no browser (`ui: false`, no Playwright MCP). Holding the feature at `built` also blocked parallel work. Both times the second qa call only wrote the verdict, and it cost an extra round-trip.

**How to apply:** On the first call, if the spec places the manual steps after handover, still flag the deviation. Ask team-leader for the decision (or point to this precedent) in the same NEEDS_ANSWER message. On the verdict call, check that HEAD and `git status --porcelain -- erp_ai` are unchanged, then skip the re-run. Add a "Sau bàn giao" checklist (owner người, before G5) and end with `Verdict: accepted`. Related: [[site-read-via-mariadb]].
