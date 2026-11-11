# Review package FEAT-001 T31

BASE=a39ee7c  head=976a1fa (branch team/FEAT-001-task-31)

Diff command (read-only, run it from the repo root): `git diff a39ee7c..team/FEAT-001-task-31`

## Commits
976a1fa feat(handlers): ticket and comment enqueue conditions via policy (FEAT-001)

## Stat
 erp_ai/handlers.py            |  63 ++++++-
 erp_ai/hooks.py               |   4 +
 erp_ai/tests/test_handlers.py | 372 ++++++++++++++++++++++++++++++++----------
 3 files changed, 350 insertions(+), 89 deletions(-)

Touchpoints: erp_ai/handlers.py, erp_ai/hooks.py, erp_ai/tests/test_handlers.py.
Criterion: AC-5(a)-(e), AC-4, NFR-1, NFR-4; design 3.2 and Amendments 2026-11-11 (D8: Comment hook, author = doc.owner only, step 0 early return with no DB read).
Expected tests: test_disabled_agent_new_ticket_no_job_no_model_call, test_new_unclassified_ticket_enqueues_one_job, test_prefilled_ticket_no_job, test_agent_created_ticket_and_comment_no_job, test_comment_keyword_case_insensitive, test_comment_on_other_doctype_or_type_no_job, test_opt_out_or_excluded_team_no_job_no_model_call, test_save_ticket_and_comment_make_no_model_call.
