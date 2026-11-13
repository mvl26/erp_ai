# Review T5 round 1 (reviewer verdict, verbatim; written by tech-lead)

Verdict: request-changes. BASE b433459..team/FEAT-003-task-5 head 15d4aa3. Structure correct (31 fields, 6 Section Breaks as in design 2.1, no Break between `value_after` and `skipped_fields`, every description ends with "Hệ thống tự ghi ... không sửa được", all < 400 chars, no sk-/@/miyano). Problem is meaning: 4 descriptions contradict the code that writes the field.

major | STD-DOC-2 | erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json:234 | `predicted_confidence` says a low confidence often stops the prediction being applied. No code does that: `set_classification` writes "Thấp" like any other value (agent/tools/write_ticket.py:39-57) | remove that sentence; say the confidence is written to the ticket's `ai_confidence` when applied

major | STD-DOC-2 | erp_ai_log.json:96 | `instructor` says it is the comment author who called the agent and is empty for a new ticket. The real value is `authority.latest_instructor()` (authority.py:72-77): the newest comment author who has the ERP AI Instructor role or was assigned by someone else, otherwise the ticket owner if they qualify. So it can be filled on `ticket_insert` rows and can be someone other than the `@ai` author. Only `reason` rows carry it (runner.py base dict ~:313) | rewrite to match; replace the test phrase "người ra lệnh" with phrases about who qualifies

major | STD-DOC-2 | erp_ai_log.json:173 | `stop_reason` gives max_turns/time_budget/gateway_error as the complete list. The code also writes the model's own stop reason (`tool_use`, `end_turn`, ...; runner.py:233,346), `unparseable` (:225) and the skip reasons `not_sendable`, `daily_limit`, `level_L0` (:95,99,106). Spec line 81 says "gồm", which does not mean "only these" | list these values or say "ví dụ"; add test phrases for `tool_use`, `not_sendable`

major | STD-DOC-2 | erp_ai_log.json:185 (+ test_doctype_descriptions.py:122) | `tools_called` says "trong lần chạy này", but each `reason` row holds only the tools of its own turn (runner.py:354). `run_id` defines a "lần chạy" as the group of rows, so the reader is misled, and the test phrase "lần chạy" locks in the wrong scope | write "trong lượt này" and change the phrase

minor (dev's call): (1) `cost_usd`:144 says the month total is added "vào ngân sách"; it is added to the amount spent (`spent_this_month_usd`, tasks.py:47). (2) `credential_label` on `gateway_error` rows is the last key tried, not a key that answered. (3) `latency_ms` on an error row shows 0, not empty. (4) the Log JSON `modified` was not bumped as design 2.1 asks (T3/T4 bumped theirs); harmless on v15 because migrate also compares the file hash.

Cannot verify: red-before-green not in the package (dev reported RED 4 failures, GREEN 9 OK, full 612 OK).
