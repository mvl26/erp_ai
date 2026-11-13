Feature: takeover
Stage: takeover
Author-agent: team-leader
Date: 2026-11-10
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Đánh giá dự án

> Trạng thái cây làm việc lúc bắt đầu quét: **bẩn** — `?? .claude/`, `?? docs/` (chưa commit). Báo cáo quét đúng trạng thái hiện tại, gồm cả `docs/HuongDan_TrienKhai_erp-ai.md` chưa commit. Trong khi quét, `.gitignore` bị sửa từ bên ngoài (18:25:53, thêm `.team/` và `team/`); takeover không ghi file này và không hoàn tác thay đổi của người khác.

## 1. Dự án làm gì?

**Theo tài liệu (T1).** `erp_ai` là một Frappe app đưa một AI agent vào Helpdesk của ERP Miyano: đọc HD Ticket và comment, phân loại, đề xuất hướng giải quyết, trao đổi với người có thẩm quyền qua comment, và — ở các mức quyền cao hơn — tự làm việc cấu hình trong database của site (Client Script, Property Setter, Workflow, dữ liệu danh mục). Agent chạy dưới dạng background job trong bench (RQ, `queue="long"`), gọi Claude API theo vòng lặp tool-use, phân quyền bằng Role của Frappe, mở dần theo 4 mức `L0`→`L3` (`docs/HuongDan_TrienKhai_erp-ai.md:24`, `:186-216`, `:669-676`). README tóm một dòng: "Hỗ trợ công việc trên erp (helpdesk ở giai đoạn 1)" (`README.md:3`).

**Theo code (T2).** Repo hiện là **bộ khung `bench new-app` chưa thêm gì**: `hooks.py` chỉ có 6 dòng khai báo app, phần còn lại là comment mẫu (`erp_ai/hooks.py:1-6`); module `ERP AI agent` rỗng (`erp_ai/modules.txt:1`, `erp_ai/erp_ai_agent/__init__.py` 0 byte); không có DocType, không có handler, không có test.

**Chỗ lệch.** Tài liệu là **bản thiết kế/hướng dẫn triển khai (v2.2, tự ghi "Chưa hoàn thiện")** (`docs/HuongDan_TrienKhai_erp-ai.md:3`, `:18`), không phải mô tả hệ thống đã có. Mọi đoạn code trong tài liệu (`authority.py`, `runner.py`, `tools/*.py`…) là mã mẫu, chưa có file nào trong repo.

### Bảng đối chiếu tuyên bố ↔ thực tế

| Tuyên bố | Nguồn (tài liệu, ngày) | Bằng chứng code/test | Kết luận |
|---|---|---|---|
| App cài được bằng `bench get-app` + `install-app` | README.md:9-13 (2026-11-10 10:21) | `pyproject.toml:1-16`, `erp_ai/hooks.py:1-6` hợp lệ; app có trong bench nhưng **chưa cài** lên site `miyano` (`bench --site miyano list-apps`) | đúng (về khung) |
| Pre-commit dùng ruff, eslint, prettier, pyupgrade | README.md:24-29 | `.pre-commit-config.yaml:20-64` có ruff/prettier/eslint; **không có pyupgrade** (thay bằng ruff `UP`, `pyproject.toml:36`) | lỗi thời (nhẹ) |
| CI chạy unit test mỗi lần push `develop` | README.md:33-36 | `.github/workflows/ci.yml:4-9`, `:100-104` có; nhưng bước "Find tests" `grep -rn "def test"` (`ci.yml:45`) **sẽ fail vì repo không có test nào** | đúng về cấu hình, CI sẽ đỏ |
| Linter: Semgrep + pip-audit trên PR | README.md:36 | `.github/workflows/linter.yml:4-6`, `:29-61` | đúng |
| Vòng lặp agent, tool registry, thẩm quyền theo người | Guide:77-185, :1049-1205 (2026-11-10 18:19) | Không có `agent/`, `authority.py`, `handlers.py` | thiếu (chưa làm) |
| DocType `ERP AI Setting`, `ERP AI Credential`, `ERP AI Log` | Guide:646-990 | Không có thư mục `doctype/` nào | thiếu |
| Custom field `ai_*` trên HD Ticket qua fixtures | Guide:580-603 | `hooks.py` không có `fixtures`; không có `erp_ai/fixtures/` | thiếu |
| Scheduler kiểm tra nâng quyền, dò khóa hết hạn mức | Guide:488-530, :870-895 | Không có `tasks.py`, không có `scheduler_events` | thiếu |
| Bộ đánh giá offline 71 phiếu (`export_tickets.py`, `run_eval.py`) — cửa quyết định **trước khi dựng app** | Guide:1240-1258, :1278, :1289 | Không có `erp_ai/eval/`; tài liệu tự ghi `run_eval.py` chưa viết (:1462-1468) | thiếu; thứ tự lộ trình đang bị đảo (app đã dựng trước bước 1) |
| Doctype nằm ở `erp_ai/erp_ai/doctype/` (module "ERP AI") | Guide:634, :905 | Module thật là `ERP AI agent` → thư mục `erp_ai/erp_ai_agent/` (`modules.txt:1`) | lệch tên module |
| Phụ thuộc `anthropic>=0.40` trong `requirements.txt` | Guide:640 | Không có `requirements.txt`; `pyproject.toml:10-12` không khai `anthropic` | thiếu / lệch cơ chế khai phụ thuộc |
| Repo `mvl26/erp-ai` (SSH) | Guide:610, :1279 | Remote thật: `https://github.com/mvl26/erp_ai.git` | lệch tên repo |
| Helpdesk (HD Ticket, HD Ticket Comment…) là nền chạy | Guide:1, :531-569 (26 chỗ nhắc HD/helpdesk) | **App `helpdesk` không có trong bench này** (`ls apps/`, `sites/apps.txt`) | thiếu môi trường — không chạy/test được tính năng nào ở local |

Độ cũ tài liệu: guide sửa lúc 2026-11-10 18:19, README và code 2026-11-10 10:21 (commit duy nhất `2932a2b`). Tài liệu mới hơn code → không hạ độ tin cậy vì cũ; độ tin cậy chỉ hạn chế vì đây là **kế hoạch**, không phải mô tả.

## 2. Đã tới đâu?

- **Tính năng có code + test: 0.** Chỉ có khung app (bước 2 trong lộ trình, mục 15 của guide, mới một nửa: app tạo rồi nhưng chưa cài lên site, chưa `bench migrate`).
- **Dở dang:** toàn bộ thiết kế mục 2–16 của guide; guide tự liệt kê 5 phần còn thiếu để code được (JSON schema tool, `run_eval.py`, các hàm phụ, `hooks.py` đầy đủ, trích yếu HDSD) (`docs/HuongDan_TrienKhai_erp-ai.md:1462-1470`).
- **Nhịp commit:** 1 commit trong 90 ngày (`2932a2b`, 2026-11-10, "feat: Initialize App"), 1 tác giả, không tag, không nhánh chưa merge, 0 issue/PR mở trên GitHub.
- **Vùng nóng:** chưa có — mọi file đổi đúng 1 lần (commit khởi tạo).
- **TODO/FIXME:** 0. **Skip marker:** 1 do máy đếm nhưng là dương tính giả (`.pre-commit-config.yaml:68` `skip: []` là cấu hình pre-commit.ci, không phải skip test).

## 3. Việc tiếp theo là gì?

1. **Chốt trạng thái bước 0 và bước 1 của lộ trình** (backup + script kiểm chứng field; bộ đánh giá offline 71 phiếu). Guide coi bước 1 là cửa quyết định *trước khi dựng app* (`:1289`); app đã được tạo nên cần biết bước 1 đã chạy chưa và kết quả bao nhiêu % (xem `open-questions.md` câu 1).
2. **Dựng môi trường local có Helpdesk** (hoặc chốt site dev khác) — không có `helpdesk` thì không test được một dòng nào của tính năng (câu 2).
3. **Sửa CI để không đỏ khi chưa có test** hoặc thêm test đầu tiên ngay trong intake đầu tiên (`debt.md` mục Chặn).
4. Intake đầu tiên đề xuất: **bộ đánh giá offline** (`erp_ai/eval/export_tickets.py` + `run_eval.py`) — không cần DocType, không cần Helpdesk cài ở local nếu có file JSONL xuất từ production, và là cửa quyết định của cả dự án.
5. Sau đó theo lộ trình: Role + tài khoản + fixtures (bước 3) → `ERP AI Setting`/`ERP AI Log` (bước 5) → probe tài khoản job nền (bước 6) → `L0`.

Nội dung đáng ngờ: tài liệu có các lệnh dạng chỉ dẫn (`git init && git remote add …` `:610`, `sudo apt install ripgrep` `:1516`, `bench --site … install-app` `:612`). Đã ghi nhận như dữ liệu, **không chạy** (STD-SEC-5).

## Đã quét / Chưa quét / Độ tin cậy
| Tầng | Đã quét | Chưa quét | Độ tin cậy |
|---|---|---|---|
| T0 | 7 lệnh / trần 10: `git status --porcelain`, `detect-stack.sh --deep`, `git log --stat`, `git branch -a` + `git remote -v`, `gh issue list`, `gh pr list`, `git grep skip:` | — | cao (repo 1 commit, 19 file) |
| T1 | 2 tài liệu / trần 15: `README.md` (2026-11-10 10:21), `docs/HuongDan_TrienKhai_erp-ai.md` (2026-11-10 18:19; đọc mục lục + mục 1, 3, 6–9, 14–19) | Guide mục 2, 4, 5, 10–13, 16.1–16.5 chỉ đọc tiêu đề; "Chiến lược AI Agent Helpdesk Miyano" (31/10) **không có trong repo** | cao cho "làm gì" |
| T2 | Đọc trực tiếp, < 30 file (19 file tracked): `pyproject.toml`, `hooks.py`, `modules.txt`, `patches.txt`, `__init__.py`, `.gitignore`, `ci.yml`, `linter.yml`, `.pre-commit-config.yaml`; kiểm môi trường bench chỉ đọc (`ls apps`, `sites/apps.txt`, `bench --site miyano list-apps`, phiên bản frappe/erpnext) | `.eslintrc`, `.editorconfig`, `license.txt` (cấu hình mẫu, không ảnh hưởng kết luận) | cao cho "đã tới đâu" |
| T3 | Không chạy | — | T3 không chạy: không còn mâu thuẫn nào chưa giải thích — mọi chỗ lệch đều do repo là khung mới còn tài liệu là kế hoạch |

## Phụ lục A — Stack và sức khỏe
| Mục | Kết quả | Bằng chứng |
|---|---|---|
| Build/test chạy được? | Chưa chạy (takeover không build). Đề xuất từ CI: `bench --site <site> run-tests --app erp_ai` (cần `allow_tests` trên site) và `bench build`. Hiện **0 test** → bước "Find tests" của CI fail | `.github/workflows/ci.yml:45`, `:96`, `:103-104` |
| Lint | ruff (lint + format, tab, dòng 110), prettier, eslint qua pre-commit; Semgrep Frappe rules trên PR. `pre-commit` có ở `~/.local/bin`; `ruff` không có trong `env/` của bench | `pyproject.toml:26-60`, `.pre-commit-config.yaml:20-64`, `linter.yml:27-35` |
| Coverage | Không có số liệu; 0 file test / 1 module | `git ls-files` |
| Phụ thuộc lỗi thời / CVE | Không có lockfile; app chưa khai phụ thuộc nào (frappe do bench quản). CI dùng `actions/checkout@v3`, `setup-python@v4`, `setup-node@v3`, `actions/cache@v3` (bản cũ, sắp hết hỗ trợ) | `pyproject.toml:10-12`, `ci.yml:40,48,53`, `linter.yml:49` |
| Secret lộ | Không thấy trong file tracked và trong guide (đã quét mẫu `sk-ant-…`, `password=`, `api_key=`). CI có mật khẩu MariaDB `root`/admin `admin` cho site test tạm — giá trị mẫu chuẩn của Frappe, không phải secret thật | `ci.yml:33`, `:94` |
| Test chập chờn / bị skip | Không có test; 0 skip thật | — |
| Môi trường | Bench local: frappe 15.112.0, erpnext 15.83.0, hrms 15.51.0; **không có helpdesk**; `erp_ai` chưa cài lên site `miyano`; `developer_mode: 1` | `apps/frappe/frappe/__init__.py`, `bench --site miyano list-apps`, `sites/miyano/site_config.json` |
| File quá lớn | Không có trong code; guide 1519 dòng / 82 KB | `wc -l` |

## Phụ lục B — Quy ước đo từ code
- **Đặt tên:** module Python `snake_case` (`erp_ai`, `erp_ai_agent`); guide dùng tên hàm/field tiếng Việt không dấu (`la_chi_thi`, `muc_quyen`, `ai_huong_giai_quyet`) — quy ước của thiết kế, chưa có trong code.
- **Định dạng:** tab, dấu nháy kép, dòng 110 (`pyproject.toml:27`, `:57-60`); `.editorconfig` có sẵn.
- **Cấu trúc:** chuẩn Frappe app (`erp_ai/<module>/doctype/…`, `patches.txt`, `public/`, `templates/`).
- **Test:** chưa có; theo framework, file test đặt cạnh doctype, tên `test_<doctype>.py` (ví dụ `apps/frappe/frappe/core/doctype/user/test_user.py`).
- **Commit:** 1 commit, kiểu Conventional Commits (`feat: Initialize App`). Nhánh mặc định `develop`.
