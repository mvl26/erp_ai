# Review T4 round 1 (reviewer verdict, verbatim; written by tech-lead)

Verdict: request-changes. BASE f7dc6b1..team/FEAT-003-task-4 head 42fbd10. 18/18 descriptions present, all <= 400, no sk-/email/miyano; 4 Section Breaks match design 2.1; AC-5 holds; T3 phrase-check cleanup is stricter, not weaker.

major | STD-DESIGN-5 | erp_ai/erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.json:47 | The `provider` description tells the admin to pick the provider that issued the key "because calls go to this provider". In the code, `gateway/credentials.py:17,46` only accepts `PROVIDER = "Anthropic"`, so an OpenAI row is never tried. The description gets the consequence wrong (breaks A-4 and the "hệ quả" point of AC-2) | Say that only Anthropic keys are used for now and an OpenAI row is skipped; add the phrase "Anthropic" or "bỏ qua" to `phrases["provider"]`

minor | STD-DESIGN-5 json:78: "tức thử sau cùng" is only true when no other row has `try_order` > 99, because `credentials.py:70` sorts by number. STD-TEST-8 test_doctype_descriptions.py:68-80: several checks cannot really fail ("khóa" for `enabled`, "lỗi", "token", "nhà cung cấp"), and `try_order` does not check "0"/"Để trống" | dev's call

Cannot verify: no red-then-green in the package (tech-lead: ask dev for it); AC-4 stored-value test compares only Setting descriptions with stored Setting values; the example "Khóa chính" at json:38 may be a real label on the site (QA to check in the AC-4 grep).
