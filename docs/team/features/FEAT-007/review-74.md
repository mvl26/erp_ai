Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 74 — FEAT-007 T74

- Diff: `git diff f2ab42ea931bfcb1ad4cc5a760a047f40249d153..3e0436c` (nhánh `team/FEAT-007-task-74`; 2 commit `e990b5b` test, `3e0436c` refactor; 5 file +212/−11, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `998b900` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ của reviewer giữ nguyên ý, finding giữ nguyên văn.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED, `MIGRATE_EXIT=0`: test_authority `AttributeError: module 'erp_ai.agent.authority' has no attribute 'enter_agent_session'` (4 test), `... has no attribute 'TITLE_WRONG_USER'` (1 test), `Ran 28 tests`, `FAILED (errors=5)`; test_architecture `'agent/runner.py:143: switches to the agent account outside agent/authority.py enter_agent_session (ADR-033 QĐ 1)'`, `FAILED (failures=1)`; test_agent_runner `test_missing_agent_user_stops`: `AssertionError: Expected 'log_error' to be called once. Called 0 times.` GREEN, một lần giữ khóa, `MIGRATE_EXIT=0`: test_authority `Ran 28 tests OK`; test_agent_runner `Ran 110 tests OK`; test_architecture `Ran 185 tests OK`.

Các phép kiểm chính của reviewer:

1. Bước (a) của `runner._run`: thân được chuyển nguyên sang `authority.enter_agent_session`: cùng phép kiểm `enabled`, cùng hai lời `log_error(TITLE_WRONG_USER, …)` (`"Không có tài khoản agent"`, `f"Sai tài khoản: {frappe.session.user}"`), dừng ở cùng các lối từ chối. `runner.py:140` nay là `if not authority.enter_agent_session(): return`, sau lối từ chối không gì chạy. Test runner ở đầu nhánh vẫn phủ ba lối từ chối, khẳng định không đổi: phiên không chuyển (`:164-170`), thiếu tài khoản agent (`:177-184`, có `gateway.call_count == 0` và phiên vẫn là Administrator), tài khoản agent bị tắt (`:187-191`).
2. Luật kiến trúc `check_set_user_agent_only_in_enter_agent_session`: chỉ quét mã sản phẩm; bắt mọi `set_user(AGENT_USER)` ngoài `authority.enter_agent_session` ở mọi dạng (đường module, từ khóa `user=`, `constants.AGENT_USER`, chuỗi tên tài khoản, import bí danh, hàm khác trong `authority.py`); đòi đúng một lần chuyển trong `enter_agent_session` (0 hay 2 đều đỏ); có mẫu sạch và các mẫu đỏ, gồm dạng runner trước T74; dòng đỏ thật là `agent/runner.py:143`. Khớp dòng Ràng buộc `docs/team/adr/ADR-033.md:55`.
3. Mỗi test của Expect đỏ khi hành vi bị trả lại: `test_switches_to_agent` kiểm `True` và người dùng của phiên; hai test tắt/thiếu kiểm đúng tham số `log_error`, `False`, phiên không đổi; `test_session_not_switched_refused_and_logged` giả `set_user` và kiểm lối "Sai tài khoản"; test kiến trúc đỏ trên runner cũ. Giá trị chờ viết cứng, lấy từ thiết kế. RED của dev khớp: 5 lỗi thiếu thuộc tính, luật đỏ ở `runner.py:143`, test runner đỏ vì `log_error` gọi 0 lần.
4. `test_agent_runner.py`: chỉ đích vá `AGENT_USER` đổi (`:177`, `runner` → `authority`), không khẳng định nào đổi.
5. Chất lượng: không dấu skip; test tự trả trạng thái (rollback và cleanup `set_user`); không nuốt lỗi; chữ log không có dữ liệu mới; `runner.TITLE_WRONG_USER` còn (import lại) nên hợp đồng cũ giữ; không phụ thuộc mới; `runner` còn dùng `AGENT_USER` ở `:184`, `:721` nên import không chết.
6. Commit: hai tiêu đề đúng `type(scope): description (FEAT-007)`; commit test đứng trước; không dòng ghi công AI.

Checklist (10): 10/10 đạt.

Findings: không blocker, không major.

- minor | — | — | 3 điểm nhỏ: (1) `U1.md:194` viết `TITLE_WRONG_USER` "chuyển chỗ" sang `authority.py`, dev giữ định nghĩa ở `constants.py:56` và import ở `authority.py:6`; hành vi và danh tính `is` như nhau, chữ thiết kế hoặc mã có thể chỉnh cho khớp. (2) chú thích trong `test_authority.py` `test_title_is_the_runner_title` viết "The title moved here", không đúng từng chữ. (3) luật không bắt lần chuyển qua biến (`u = AGENT_USER; frappe.set_user(u)`) hay gán thẳng `frappe.session.user = AGENT_USER`; chữ `ADR-033:55` không đòi | dev's call

Mục "không kiểm được từ diff" của reviewer:

- Reviewer không chạy test; GREEN chỉ có đầu ra của dev.
- Tech-lead có nhận việc giữ `TITLE_WRONG_USER` ở `constants.py` thay vì chuyển như `U1.md:194` viết hay không (chữ thiết kế, không đổi hành vi).
- Ghi chú quy trình: dev nối lớp test vào `test_authority.py` bằng heredoc Bash thay vì Edit; trái quy tắc handbook, không phải lỗi mã.

## Kết luận của tech-lead

- Chạy test: sau merge `998b900`, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_authority `Ran 28 tests in 47.805s OK`, test_agent_runner `Ran 110 tests in 59.012s OK`, test_architecture `Ran 185 tests in 28.330s OK`.
- `TITLE_WRONG_USER` ở `constants.py`: dòng Returns của T74 chỉ đòi tên `authority.TITLE_WRONG_USER` có và tên `runner.TITLE_WRONG_USER` còn; cả hai đúng, test `test_title_is_the_runner_title` ghim. Chuyển định nghĩa sang `authority.py` đòi sửa `erp_ai/constants.py`, file ngoài `files:`. Nhận như hiện có; chữ "chuyển chỗ" của `U1.md:194` ghi cho As-Built. Không mở vòng sửa.
- Heredoc của dev: ghi vào dòng DỪNG lượt 16 (mục tự báo); kết quả trên nhánh là commit bình thường, pre-commit qua.

## deferred

- minor (1), (2): chữ thiết kế `U1.md:194` và chú thích test → As-Built / `/team:clean`.
- minor (3): giới hạn của luật (không lần theo biến) → ghi cho As-Built cùng các giới hạn luật của T83.
