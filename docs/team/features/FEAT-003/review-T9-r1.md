# Review T9 round 1 (reviewer verdict, verbatim; written by tech-lead)

Verdict: request-changes. BASE c3f32b5..team/FEAT-003-task-9 head 7cb9853. Code meets design 3.2 steps 1-3 and 5, F2 order (gate -> AGENT_USER refusal -> text checks -> build -> one `new_comment`); constraints hold (one `.new_comment(`, POST, no guest, no forbidden calls, no agent-gate evaluation, no sanitize/log yet = T10).

major | STD-TEST-5 | erp_ai/tests/test_ticket_panel.py:398 | The escape test passes with `html.escape` removed. `Comment.validate` runs bleach `clean` with strip=False (frappe/utils/html_utils.py:195-202), which escapes `<script>` and `&` on its own. So `&lt;script&gt;` and `&amp;` show up and `<script>` is gone either way. `<b>` is an allowed tag and would stay | Use the spec's data `<b>x</b> & y`. Assert the exact stored text `<p>&lt;b&gt;x&lt;/b&gt; &amp; y ...</p>`. Add the round trip from design test plan row 340: `get_panel_data` returns `<b>x</b> & y`

major | STD-TEST-5 | erp_ai/tests/test_ticket_panel.py:359 (used at 392, 404, 425) | The send tests seed the keyword as `KEYWORD="@ai"`. If `ticket_panel.py:104-106` hard-codes `" @ai"` behind `if keyword`, every T9 test stays green. Spec AC-9 says do not hard-code `@ai`, and design row 337 asks for an unusual keyword | Seed an unusual keyword without `<>&` (for example `!hoibot`) in `TestTicketPanelSend.setUp`, and use it in the expected strings. Keep the other-case test using the same keyword in a different case

minor (dev's call): no inactive-HD-Agent or HD Contact case on send (design: "ở cả hai" / "các tài khoản trên"); the no-read precondition (`is_agent()` True, `has_permission` False) not re-asserted at :431; length after `strip()` not tested (e.g. `"  "+"a"*2000+"  "`); `send_message` has no docstring (STD-DOC-7); `assertRaises(TypeError)` should be `frappe.FrappeTypeError`.

Accepted: text=None/5 raising FrappeTypeError (frappe.whitelist validate_argument_types, 417 like ValidationError) before the body, 0 Comment; design 3.2 error table row 172 to be reworded at As-Built.

Mutations the tests do catch: keyword appended every time; `>=` or `>2001` length; owner = AGENT_USER; no gate (NO_READ subtest); `forbid_agent_user` dropped; missing ticket raising DoesNotExistError; case-sensitive keyword check; line-break join.

Cannot verify: red-then-green (dev reported RED AttributeError no `send_message`; GREEN test_ticket_panel 31 OK, test_architecture 60 OK; step-0 full `Ran 625 tests ... OK` on c3f32b5); whether `<br>` comes back from bleach unchanged in the multiline exact-match test.
