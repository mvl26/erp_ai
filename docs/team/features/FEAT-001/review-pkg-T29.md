# Review package FEAT-001 T29

BASE=a39ee7c  head=a291535 (branch team/FEAT-001-task-29)

Diff command (read-only, run from the repo root): `git diff a39ee7c..team/FEAT-001-task-29 -- erp_ai/`

## Commits
a291535 feat(agent): T29 runner L1 applies classification via set_classification (FEAT-001)

## Stat (code)
 erp_ai/agent/runner.py      |  66 ++++++++++++++--
 erp_ai/agent/test_runner.py | 137 ++++++++++++++++++++++++++++++++-
(the dev report file under docs/ is excluded from the review)

Touchpoints: erp_ai/agent/runner.py, erp_ai/agent/test_runner.py.
Criterion: AC-10 (L1 writes mapping + confidence + "classified by = AI", status unchanged, human-classified not overwritten); ADR-004 (runner updates `applied` of its own `classify` log row). Mandatory debt (review-34 deferred): `applied = 1` only when `after` is non-empty; tool write and classify-row update together, never ticket changed with applied=0.
Expected tests: test_l1_applies_mapping_confidence_and_hint (classification part), test_l1_human_classified_not_overwritten.
