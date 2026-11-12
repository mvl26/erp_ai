# Review T2 round 1 (reviewer verdict, verbatim; written by tech-lead)

Verdict: request-changes. BASE 1560098..team/FEAT-003-task-2 head 31c4b75. Criteria met by reading; textContent-only (AC-12) holds; all 18 old forbidden strings remain, 14 ADR-009 strings added; static rules not decorative; JS handles no socket, width < 640, reset, stale results.

major | STD-DESIGN-2 | erp_ai/public/js/agent_status_indicator.js:227 (constant at :4) | `state.call(METHOD_GET_PANEL_DATA, …)` passes a variable as the first argument. ADR-009 requires a string literal in every `call(`, and design 3.3 and 4 show the literal. Because `\bcall\b` is gone and no allow-list test exists until T15, nothing checks this now, and the T15 scanner will either go red or be written loosely to fit | Write `state.call("erp_ai.ticket_panel.get_panel_data", { ticket })` and delete `METHOD_GET_PANEL_DATA`

minor (dev's call): (a) If `state.call` is missing or throws synchronously, `togglePanel`'s catch hides it and the panel opens blank with no "Không tải được…" message (js:226,257-259); design F5 treats bad data as a load error. (b) Suspected: a `window.__erpAiAgentStatus` object created by an older version of the script (script updated while the page stays open) has no `panel`; `reset()` then throws at js:273 and the ticket switch and `doc_subscribe` are skipped. (c) A panel already open stays open when narrowed; plan leaves this to T14 `onResize`.

Cannot verify: no test output in package (tech-lead: dev reported RED 1 failure test_status_script_static_rules for the missing signature; GREEN test_architecture 58 OK, test_install 22 OK, full 611 OK); AC-6/AC-7 page behaviour covered by manual J1 only.

For T15 / design gap (deferred): ADR-009 forbidden list misses `setAttribute("src"|"href", …)`, `removeEventListener`, `innerText +=`, `createElement("A")` (uppercase).
