# Review T12 round 1 (reviewer verdict, verbatim; written by tech-lead)

Verdict: request-changes. BASE da2d63e..team/FEAT-003-task-12 head 866e577. The JS itself is correct (textContent only, stale guard, docking, reset, error text). Only the static test is weak.

major | STD-TEST-2 | erp_ai/tests/test_architecture.py:162-172 | The new REQUIRED regexes match declarations, not the places they are used. Each of these deletions in agent_status_indicator.js keeps every check green: `renderMessages(data);` (:293), `if (isStale()) return` (:289-291, the AC-11(g) guard), `dockIndicator(true/false)` (:315/:213), `textContent = TEXT_BOT_GUIDANCE` (:187), `TEXT_EMPTY_THREAD` (:244), `TEXT_BOT_LABEL` (:256) and `panel.threadEl.replaceChildren()` (:336). `threadEl` already matches the state key at :33 | Keep the exact-string pins and add use-site patterns: `renderMessages\(data\)`, `if \(isStale\(\)\) \{\s*return;`, `dockIndicator\(true\)`, `dockIndicator\(false\)`, `textContent = TEXT_(BOT_GUIDANCE|EMPTY_THREAD|CLOSE)`, `\? TEXT_BOT_LABEL :`, `threadEl\.replaceChildren\(\)`

minor (dev's call): (1) js:292-293: if `renderAiFields` succeeds and `renderMessages` then throws, the new AI fields show next to the old thread plus the error text. (2) js:334-336: `reset` checks only `aiListEl` before using `threadEl` (only matters for an unreleased T2/T7 panel state left in a dev window).

Cannot verify: red/green output (dev reported RED "missing in script: threadEl", GREEN test_architecture 60 OK, test_install 22 OK, lint clean); AC-6/8/11/12 page behaviour is manual (J1).
