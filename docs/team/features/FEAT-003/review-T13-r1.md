# Review T13 round 1 (reviewer verdict, verbatim; written by tech-lead)

Verdict: request-changes. BASE c3f32b5..team/FEAT-003-task-13 head 3f21d1d. JS meets criteria (empty / > 2000 -> no call; literal `send_message` call; Enter only without Shift and isComposing false; success clears and reloads; failure keeps text; textContent only; `sending` always released; stale guard comparing ticket only is defensible because every reload bumps `seq`). No test line removed or loosened.

major | STD-TEST-2 | erp_ai/tests/test_architecture.py:185-205 | Same defect as T12 r1. `panel.sending = false` matches only the line inside the unlock arrow (js:371), not where unlock is called. Each of these JS edits keeps every check green:
  - delete `unlock();` at :377 (the lock never releases after the first success) or at :390;
  - `.then(onSent, onSendFailed)` -> `.then(onSent)` at :405;
  - delete `onSendFailed();` in the catch at :407;
  - delete `submit();` at :209 or :220;
  - drop `formEl` from `el.append` at :235;
  - change send's `isStale` (:369) to `() => false`, or delete it at :378. `if \(isStale\(\)\) \{\s*return;` already matches reload's copy at :336, so it does not cover send.
  Also, adding `panel.inputEl.value = ""` inside unlock stays green, despite the "nothing else happens" comment.
  | Pin each wiring point: `unlock\(\);\s*if \(isStale\(\)\) \{\s*return;\s*\}\s*panel\.inputEl\.value = ""`, `onSendFailed = \(\) => \{\s*try \{\s*unlock\(\);\s*if \(!isStale\(\)\)`, the whole unlock body (`unlock = \(\) => \{\s*panel\.sending = false;\s*panel\.sendEl\.disabled = false;\s*panel\.sendEl\.textContent = TEXT_SEND;\s*\}`), `\.then\(onSent, onSendFailed\)`, `catch \(e\) \{\s*onSendFailed\(\);`, `isComposing\) \{\s*event\.preventDefault\(\);\s*submit\(\);`, `addEventListener\("click", \(\) => \{\s*try \{\s*submit\(\);`, `const isStale = \(\) => ticket !== state\.ticket;`, `formEl,\s*slotEl`

minor (dev's call): (1) js:369 a P->Q->P round trip while a send is pending lets the late reply clear text typed after coming back (a reset-only counter would fix it). (2) js:381 the textarea stays editable while sending, so edits made during the send are lost on success. (3) `value.length` counts UTF-16 units vs Python code points: page stricter on emoji, never looser. (4) the 3.3 values of `TEXT_SEND`, `TEXT_INPUT_PLACEHOLDER` and `sendEl.disabled = true` (:400) are not pinned. (5) Safari may fire Enter with isComposing=false right after the IME ends.

Cannot verify: red-then-green (dev reported RED `missing in script: TEXT_SEND_FAILED`, GREEN test_architecture 60 OK, test_install 22 OK, mutation table 7/7 RED); real Enter/IME/double-click/network-failure/ticket-switch behaviour is manual (J1 step 3, AC-11(g)).
