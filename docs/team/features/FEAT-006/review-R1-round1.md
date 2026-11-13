# Review R1 (T19, rework 1) — vòng 1: request-changes

Diff: `git diff df8de66..team/FEAT-006-rw1-r1` (commit 85c31cd). Reviewer: team:reviewer (nguyên văn bên dưới).

major | STD-DESIGN-3 | erp_ai/gateway/__init__.py:152-153 | Classify now always sends `thinking: {"type": "disabled"}`, whatever the model. But `model_classify` and `model_classify_default` are free-text fields documented to accept any provider model (erp_ai_credential.json:61, erp_ai_setting.json:148). Sonnet 5.5, Opus 5.5 and Fable all reject `disabled` with a 400. On a 400 the gateway gives up with `bad_request` and does not try another key (`__init__.py:167-168`). So any site that set one of those models would lose all classification, where before it worked. | Send `disabled` only to models that accept it (e.g. a `claude-haiku-` prefix check or a small allow-list constant), and add a test that a non-Haiku classify request has no `thinking`. Alternatively validate the field on save and update its description.

minor | STD-DOC-4 | design.md D-8 | still says "raise the ceiling when max_tokens is hit"; should record: thinking off for classify, ceiling stays 600. -> deferred (designer/asbuilt).

Not verifiable from the diff: E1/E2 figures (qa re-runs E2); which models the miyano site configures.
