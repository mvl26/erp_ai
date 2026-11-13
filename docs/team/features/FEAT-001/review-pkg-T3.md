# Review package T3 (FEAT-001)

Diff command: `git diff a351af1..team/FEAT-001-task-3` (BASE=a351af1, head fb3be74)
Commits: fb3be74 feat(agent): classification prompts, parser, category mapping (FEAT-001)
Stat: erp_ai/agent/classification.py (+122), erp_ai/agent/prompts.py (+206), erp_ai/agent/test_classification.py (+310), all new.

Run the diff command in /home/miyano/frappe-bench/apps/erp_ai (branch is local).
Criteria (tasks.md T3): AC-3 (non-JSON / bad values -> parse_classification returns None); AC-10 pure branch (category mapping D-8, urgent tag in the subject forces urgent priority); validate_mapping rejects a bad schema with ValidationError.
Returns required: prompts.build_classify_request, ticket_text, build_reason_system, build_initial_message; classification.Classification, parse_classification, load_mapping, validate_mapping, resolve_ticket_values, DEFAULT_CATEGORY_MAPPING.
Touchpoints: erp_ai/agent/prompts.py, erp_ai/agent/classification.py, erp_ai/agent/test_classification.py.
Compare the exact urgent-tag spelling, the prompt text and the default mapping against spec.md / design.md in docs/team/features/FEAT-001/.
