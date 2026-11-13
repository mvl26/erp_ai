Feature: takeover
Stage: onboard
Author-agent: team-leader
Date: 2026-11-11
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Onboarding

Điều kiện: G0 đã duyệt (`docs/team/ai-readiness.md:5` `Approved-by: Hieu 2026-11-11`), `Verdict: adjust-profile` (`:11`). Profile lấy từ `profile-proposal.md`; `<site>` chốt là `miyano` (site duy nhất trong bench, `default_site`, `allow_tests: true`, đã cài `erp_ai` — `bench --site miyano list-apps`).

## Đã tạo / bỏ qua / việc tay
Kit: `team` 0.4.0. Lần chạy lại onboard chỉ được ra "bỏ qua (đã có)" cho mọi dòng dưới đây.

| Trạng thái | File | Cách ghi (tạo / gộp JSON / chèn khối / bỏ qua) | Nguồn mẫu | Ghi chú |
|---|---|---|---|---|
| đã tạo | `.team/profile.json` | tạo | `docs/team/profile-proposal.md` | `check-profile.py` exit 0 |
| đã tạo | `.team/config.json` | tạo | `templates/project/team/config.json` | `check-profile.py` exit 0; `output_language: vi`, `default_mode: ask`, `base_branch: main` |
| đã tạo | `CLAUDE.md` | chèn khối | `templates/project/CLAUDE.md.tmpl` | file mới; khối 16 dòng (`awk … \| wc -l`) |
| đã gộp | `.claude/settings.json` | gộp JSON | `claude/settings.json.tmpl` | giữ `enabledPlugins` cũ; thêm `agent`, `permissions`, `skillOverrides: {}` |
| đã tạo | `.claude/settings.local.json` | gộp JSON (file mới) | `claude/settings.local.json.tmpl` | đường dẫn kit của máy này; bị gitignore |
| đã tạo | `.claude/rules/source.md`, `team-core.md`, `tests.md`, `tool-map.md` | tạo | `claude/rules/*.md.tmpl` | `tests.md` có path `colocated/**` (vô hại; `**/*test*` mới là pattern có tác dụng) |
| đã tạo | `.github/workflows/team-ci.yml`, `team-feature.yml` | tạo | `github/workflows/` | `ci.yml`, `linter.yml` giữ nguyên. Xem việc tay về `team-ci.yml` |
| đã tạo | `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/team-feature.yml`, `.github/CODEOWNERS` | `cp --update=none` | `github/` | CODEOWNERS còn `@<owner>` |
| đã tạo | `docs/team/{features,adr,research,metrics,retro,proposals,agents}/` | tạo | — | |
| bỏ qua | `docs/team/explore/`, `docs/team/journal/` | bỏ qua (đã có) | — | |
| đã tạo | `docs/team/skills-registry.md`, `docs/team/kit-issues.md` | tạo | `templates/artifacts/vi/` | |
| đã gộp | `.gitignore` | thêm dòng thiếu | `gitignore.tmpl` | thêm 6 dòng runtime; dòng `.team/` của người giữ nguyên (xem việc tay) |

## Chạy thử một lần
`git status --short` trước và sau (bỏ qua các file onboard vừa tạo): không có thay đổi; không đụng lockfile hay `protected_paths`.

| Khe | Lệnh | Mã thoát | Đầu ra (trích) |
|---|---|---|---|
| cmd.install | `cd ../.. && bench setup requirements --dev && bench --site miyano install-app erp_ai` | 0 | `uv pip install --quiet coverage~=6.5.0 … freezegun~=1.2.2` … `App erp_ai already installed` |
| cmd.lint | `pre-commit run --all-files` | 1 | mọi hook Passed/Skipped trừ `Run ruff formatter…Failed — 1 file reformatted, 6 files left unchanged` (`erp_ai/hooks.py`, xóa dòng trống cuối). Onboard đã hoàn tác (`git checkout -- erp_ai/hooks.py`); ghi vào `debt.md` |
| cmd.test | `cd ../.. && bench --site miyano run-tests --app erp_ai` | 0 | `Ran 0 tests in 0.000s` / `NO TESTS RAN` — chưa có test nào |

`grep -c '{{'` trên `CLAUDE.md`, `.claude/settings.json`, `.claude/settings.local.json`, `.claude/rules/*.md` = 0 cho mọi file. (Trong `.github/workflows/` chỉ có biểu thức GitHub `${{ … }}`, không phải chỗ trống.)

## Plugin khuyên dùng (chưa cài)
- Bắt buộc: `team@automation-ai` — đã bật (`.claude/settings.json`).
- Khuyên dùng: không có (profile để rỗng).
- Plugin trùng chức năng đang bật ở cấp user: `superpowers@claude-plugins-official`. Nếu giữ, cân nhắc ẩn skill trùng trong `.claude/settings.json`:
  `"skillOverrides": {"superpowers:brainstorming": "user-invocable-only", "superpowers:writing-plans": "user-invocable-only", "superpowers:executing-plans": "user-invocable-only", "superpowers:subagent-driven-development": "user-invocable-only", "superpowers:requesting-code-review": "user-invocable-only", "superpowers:finishing-a-development-branch": "user-invocable-only"}`

## Việc người phải làm tay
- **`.gitignore:9` `.team/`** (dòng người thêm) làm git bỏ qua `.team/profile.json` và `.team/config.json` (`git check-ignore -v`), mà hai file này cần được commit. Đề xuất bỏ dòng `.team/`: các file runtime trong `.team/` đã có dòng ignore riêng.
- **`.github/workflows/team-ci.yml`** sinh thẳng từ profile sẽ đỏ trên GitHub: runner không có bench, site `miyano` hay pre-commit (bước Setup là `true`). `ci.yml` có sẵn đã dựng bench đúng cách. Đề xuất: xóa `team-ci.yml` trước khi commit, hoặc đặt `ci.setup` trong profile rồi sinh lại bằng `/team:ci`.
- **`.github/CODEOWNERS`**: thay `@<owner>` bằng người/nhóm thật (hoặc xóa file).
- **Secret `ANTHROPIC_API_KEY`** trên GitHub nếu dùng `team-feature.yml`; runner cần `--allowedTools` (đã có trong mẫu, K-06).
- **Quyền rộng trong `.claude/settings.json`**: `Bash(python3 *)` (có từ mẫu) và `Bash(cd ../.. && bench --site miyano run-tests --module "$(echo *)` (tiền tố của `cmd.test_one` bị cắt ở `$(`) — xem lại và thu hẹp nếu cần.
- **`cmd.test_one`** chưa chạy thử được (0 test) — kiểm với file test đầu tiên.
- `config.json`: `output_language` đang là `vi` (đổi sang `en` nếu muốn); `approvers` đang rỗng; `base_branch: main` trong khi repo chỉ có nhánh `develop` (open-questions câu 10).
- `docs/team/open-questions.md` chưa trả lời câu nào; câu 1 (bước đánh giá offline) và câu 2 (helpdesk trên bench dev) ảnh hưởng trực tiếp tới intake đầu tiên.
- Commit các file trên (không commit `.claude/settings.local.json`).
