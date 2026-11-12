# Review T7 round 1 (reviewer verdict, verbatim; written by tech-lead)

Verdict: request-changes. BASE 3cfa6bf..team/FEAT-003-task-7 head 32dd12e. B-5 selection, old->new order and the `{name, author, is_bot, created_at, text}` keys (no email) match design 3.1. Pinned timeline keys check out against activity.py:254-271,331-337. Permissions fine (no ignore_permissions in production code; gate runs before `_thread`). The literal `<script>` text left after `html_to_plain_text` is accepted (AC-12 allows "chuỗi hiện ra dưới dạng chữ (hoặc mất thẻ)", page uses textContent).

major | STD-TEST-2 | erp_ai/tests/test_ticket_panel.py:183-197 | AC-8's test data is cut down. The spec asks for 3 human comments with the keyword (1 in different case), 2 without, 2 from the agent, and 1 keyword comment on another ticket, giving exactly 5 messages; the T7 Expect line also says 5. The test seeds 2/3/2, asserts 4, and has no comment on another ticket, so "comments of another ticket do not show" is never tested | Add a third human keyword comment and a keyword comment on a second `make_ticket`, then assert the 5 names in order

minor (dev's call): (1) the keyword is matched on markdown-rendered content (load.py:169), not the stored content the handler sees, so a keyword with `_`/`*` could drift from the gate; (2) a deleted user's author falls back to the owner email (activity.py:335); (3) `created_at` "12-11-2026 10:02:00" assumes the site's date format; (4) the AC-12 data sits in a human comment, not a bot one.

Cannot verify: red-then-green not in the package (dev reported RED 4 failed + 1 error, GREEN 16 OK, test_architecture 60 OK); `get_document_comments` hiding rows from agents (outside the diff); zero writes on the read path is T8.
