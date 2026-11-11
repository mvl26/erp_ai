Feature: takeover
Stage: takeover
Author-agent: team-leader
Date: 2026-11-10
Approved-by: Hieu 2026-11-11

<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# AI-readiness

Verdict: adjust-profile

Luật dẫn tới kết luận: không có file ngữ cảnh AI nào (CLAUDE.md, AGENTS.md) để mâu thuẫn với code → không có gì phải dọn trước (`clean-first` không áp dụng); nhưng profile `python` mặc định của kit sai với một Frappe app ở hầu hết khe lệnh (`pytest`, `pip install -e`, `alembic`, `src/`, `tests/`) → phải chỉnh profile theo `profile-proposal.md` (`adjust-profile`), không thể `ready`.

Đã cân nhắc `clean-first` vì repo có 0 test: không chọn, vì repo chưa có hành vi nào cần lưới an toàn bảo vệ (chỉ là khung `bench new-app`); test sẽ ra đời cùng tính năng đầu tiên. Nếu người duyệt muốn chặn cứng tới khi CI xanh thì đổi dòng `Verdict:` thành `clean-first` khi duyệt G0.

## Hiện trạng

| Mục                                       | Có                                                                               | Giữ / Cắt / Viết lại          | Lý do                                                                                                                    |
| ------------------------------------------ | --------------------------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| CLAUDE.md (0 dòng, không có)            | Không                                                                            | Viết mới (do `/team:onboard`) | `ai_files: {}` từ detect-stack. Nên gồm: lệnh bench, site dev, "agent không sửa `apps/` khác", trỏ tới guide |
| .claude/ (settings, agents, skills, rules) | Có: `.claude/settings.json` (chưa commit) — chỉ bật `team@automation-ai` | Giữ                              | Đúng một khóa `enabledPlugins`, không có quyền/hook lạ                                                          |
| Plugin đã cài                           | `team@automation-ai` (bật ở cấp project)                                     | Giữ                              | Cần cho quy trình đội                                                                                                 |
| MCP                                        | Không có cấu hình MCP cấp project                                            | —                                | Không có gì để giữ/cắt                                                                                             |
| AGENTS.md                                  | Không                                                                            | —                                | Không cần thêm; CLAUDE.md là đủ                                                                                     |

## Mâu thuẫn với code

- Không có file AI nào → không có mâu thuẫn trực tiếp.
- Tài liệu dự án (`docs/HuongDan_TrienKhai_erp-ai.md`) sẽ là nguồn ngữ cảnh chính cho agent; nó lệch code ở 3 điểm cần sửa hoặc ghi chú trước khi agent dùng nó làm chỉ dẫn: tên module (`erp_ai/erp_ai/doctype/` ở `:634` vs `erp_ai/erp_ai_agent/` thật), `requirements.txt` (`:640`) vs `pyproject.toml`, tên repo `erp-ai` (`:610`) vs `erp_ai`.

## Việc trước khi onboard

- **`.gitignore:10` có mẫu `team/`** (thay đổi chưa commit, xuất hiện lúc 18:25:53 trong khi quét, không do takeover ghi) — mẫu này khớp *mọi* thư mục tên `team`, nên `docs/team/` (nơi đội ghi spec, design, plan, journal, và 5 báo cáo này) **bị git bỏ qua** (`git check-ignore -v docs/team/assessment.md` → `.gitignore:10:team/`). Cần người quyết: đổi thành `/team/` hoặc bỏ dòng, nếu muốn các artifact của đội được version.
- Commit hoặc quyết định số phận của `docs/HuongDan_TrienKhai_erp-ai.md` và `.claude/settings.json` (đang untracked).
- Chốt site dev và việc cài `helpdesk` vào bench local (xem `open-questions.md` câu 2) — profile cần tên site cho mọi lệnh `bench --site`.
- Duyệt `profile-proposal.md`, nhất là `cmd.test_one` (chưa chạy thử được vì chưa có file test).

## Đã quét / Chưa quét / Độ tin cậy

| Tầng | Đã quét                                                        | Chưa quét                                                | Độ tin cậy |
| ----- | ----------------------------------------------------------------- | ---------------------------------------------------------- | ------------- |
| T0    | `detect-stack.sh --deep` (`ai_files: {}`), `ls -la .claude` | Cấu hình Claude cấp user (`~/.claude`) — ngoài repo | cao           |
| T1    | `.claude/settings.json` (4 dòng), guide (như assessment)      | —                                                         | cao           |
| T2    | `.gitignore` + `git check-ignore`                             | —                                                         | cao           |
| T3    | Không chạy: không có mâu thuẫn chưa giải thích           | —                                                         | —            |
