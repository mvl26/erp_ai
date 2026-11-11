hash: 8acc20d483dd0fc4

# Explore cache — erp_ai (takeover 2026-11-10)

- Stack: Frappe app (`erp_ai/hooks.py:1-6`), frappe ~=15 do bench quản (`pyproject.toml:11`); bench local frappe 15.112.0, erpnext 15.83.0, hrms 15.51.0, **không có helpdesk**.
- Trạng thái: khung `bench new-app` nguyên bản, 1 commit (`2932a2b`), 19 file, 0 test, 0 DocType, module `ERP AI agent` rỗng.
- Tooling: ruff (tab, dòng 110), prettier, eslint qua pre-commit; CI GitHub: `run-tests --app erp_ai` (`ci.yml:104`), Semgrep + pip-audit trên PR.
- Tài liệu: `docs/HuongDan_TrienKhai_erp-ai.md` v2.2 (untracked) — thiết kế AI agent cho Helpdesk: background job, Claude tool-use, Role-based authority, mức quyền L0–L3, DocType `ERP AI Setting`/`Credential`/`Log`, lộ trình 10 bước với bước 1 (eval offline) là cửa quyết định.
- Lệch chính: module thật `erp_ai_agent` vs guide `erp_ai/erp_ai/doctype`; `.gitignore:10` `team/` ignore `docs/team/`; CI fail khi 0 test (`ci.yml:45`).
