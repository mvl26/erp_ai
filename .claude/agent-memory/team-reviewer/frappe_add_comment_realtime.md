---
name: frappe-add-comment-realtime
description: Frappe 15.126.1 add_comment always publishes doc_update + list_update; designs saying "0 publish_realtime" mean "no call of our own"
metadata:
  type: project
---

In Frappe 15.126.1, `Document.add_comment(...)` inserts a Comment, and every insert runs `notify_update` (frappe/model/document.py:1341-1343, 1370-1385). So you always get two after-commit `publish_realtime` calls, `doc_update` (Comment, name) and `list_update`. `Comment.notify_change` sends `docinfo_update` only for the types Like/Assigned/Comment/Attachment, never for `Info` (comment.py:85-97).
Seen twice: the CHG-001 `post_result` test pins exactly those two events, and CHG-002 T31 (2026-11-15) design-addendum-3 RQ-4 said "publish_realtime 0 lần gọi". Taken literally, that cannot be done while also using the add_comment call the design requires.

**Why:** design text keeps saying "0 publish_realtime" for Info comments. The real intent is "no call of our own" (the AST/grep rule in result_comment.py).
**How to apply:** do not flag a test that pins exactly [doc_update Comment, list_update] as a defect of the diff. Report the literal "0 calls" wording as an imprecise design text for the designer to reword. It does not block. Related: [[recurring_masked_tests]].
