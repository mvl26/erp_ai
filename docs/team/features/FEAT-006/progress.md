# Progress FEAT-006

Edit không có trong bộ công cụ của tech-lead; tick và đổi touchpoint nằm ở đây, gộp vào `tasks.md` khi xong. Dòng ở đây thắng `tasks.md` khi lệch.

Quy trình:

- role-policy chặn tech-lead chạy `PYTHONPATH=... bench ...`: `cmd.test` do dev chạy trên đầu nhánh task. Tech-lead kiểm cây mã sau merge bằng `git diff --stat <head task> team/FEAT-006 -- . ':!docs'` (rỗng = cây mã trùng đầu nhánh đã chạy xanh).
- Site `miyano` dùng chung: hai `cmd.test` đồng thời gây `QueryDeadlockError 1213` giả (R1: 37 error; T4/T5 song song: 45 và 34 error). Từ sau T5: MỘT dev mỗi lần; reviewer chạy song song với dev kế tiếp được vì reviewer không chạy bench.
- Nhánh task đang được checkout trong worktree dev cũ thì dev sửa vòng sau tạo nhánh `-reworkN` (hoặc `-cont`); tech-lead `merge --ff-only` vào nhánh task từ worktree của dev cũ, hoặc merge thẳng nhánh mới.
- `review-NN.md`: NN = số task (T9b → `review-09b.md`).
- BASE của task = `git rev-parse team/FEAT-006` ngay trước lần gọi dev; ghi vào dòng tick (commit docs đứng trước lần gọi dev nên BASE là đầu nhánh sau commit docs đó).

## Đổi touchpoint

- T1 (người duyệt 2026-11-12): thêm `erp_ai/agent/test_agent_runner.py`, `erp_ai/agent/test_runner_status.py`, `erp_ai/tests/test_install.py`. Chỉ sửa kỳ vọng cũ (STD-TEST-5).
- T6 (tech-lead; team-leader chấp nhận ngày 2026-11-12, journal "quyết định 4 điểm"): thêm `erp_ai/agent/test_runner_routing.py`, chỉ đổi `priority == "High"` → `"Urgent"` cho A + quan trọng 3 (kỳ vọng của bản giả T1 trái R4/AC-3).
- T11 (tech-lead; team-leader chấp nhận ngày 2026-11-12): thêm `erp_ai/tests/test_doctype_descriptions.py`, chỉ thêm dữ liệu ghim (`field_count` 22 → 24 và `phrases` cho `auto_assign_enabled`, `routing_rules`); không nới khẳng định cũ.
- T9b (task chèn mới, quyết định (1)+(3) của team-leader): touchpoint `erp_ai/agent/routing.py`, `erp_ai/agent/test_routing.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`; depends: T9, T11.

## Tick

- [x] T1 — BASE=d8fb3e9, 2 vòng, merge 2393337, review-01, cmd.test 660 OK
- [x] T3 — BASE=4cfd68f, 1 vòng, merge d4a766c, review-03, cmd.test 664 OK
- [x] T6 — BASE=4cfd68f, 1 vòng, merge b8d2607, review-06, cmd.test 668 OK
- [x] T4 — BASE=b1af21f, 1 vòng, merge 6ebb766, review-04; test_one xanh; cmd.test nối tiếp: xem dòng nền 703 OK bên dưới
- [x] T5 — BASE=b1af21f, 1 vòng, merge 1aa1a79, review-05; test_one xanh; cmd.test nối tiếp: xem dòng nền 703 OK bên dưới
- [x] T7 — BASE=686aa3f, 2 vòng, merge 2851bca, review-07; dev cmd.test 679 OK (vòng 1)
- [x] T2 — BASE=686aa3f, 2 vòng, merge 8473884, review-02; dev cmd.test 687 OK
- [x] T8 — BASE=2851bca, 2 vòng, merge 61e51f2, review-08; dev cmd.test 688 OK (vòng 1)
- Nền nối tiếp (T4, T5, T7, T2, T8 gộp): `cmd.test` trên cây mã của 61e51f2 (đồng nhất với 8c5af9c): Ran 703 tests, OK.
- [x] T9 — BASE=8c5af9c, 3 vòng (2 vòng sửa), merge 896b7ac, review-09; cmd.test đầu nhánh task 989c37d: Ran 710 tests, OK
- [x] T10 — BASE=7fa9ad9, 1 vòng, merge a9e7e2e, review-10; cmd.test đầu nhánh task 2f0b871: Ran 723 tests, OK
- [x] T11 — BASE=f1a732b, 1 vòng (sau DESIGN_CONFLICT được giải), merge 27d18fe, review-11; cmd.test đầu nhánh task 776839a: Ran 728 tests, OK
- [x] T12 — BASE=449e2b5, 2 vòng, merge 1f0b3f7, review-12; cmd.test đầu nhánh task 1db4533: Ran 738 tests, OK
- [x] T9b — BASE=8a1bd31, 2 vòng (1 vòng sửa), merge 4dc14d7, review-09b; cmd.test đầu nhánh task 566f796: Ran 744 tests, OK

## Checkpoint C2 (trên 1f0b3f7)

- `bench --site miyano migrate` (cmd.migrate): exit 0; chỉ có dòng `Updating DocTypes for erp_ai ... 100%` và `Updating Dashboard for erp_ai`, không lỗi.
- `ensure_setup` chạy hai lần (sau migrate đã chạy một lần qua after_migrate): ảnh chụp 2 và 3 bằng nhau ở `Task-ai_ticket` (mọi cột, kể cả modified), dòng Custom DocPerm Task/ERP AI Agent (share 1, if_owner 1), `routing_rules` và `auto_assign_enabled` trong tabSingles, 11 field `ai_*` của HD Ticket, Has Role của tài khoản agent (99 dòng), HD Form Script, User; tổng Custom Field 247, Custom DocPerm 1360.
- `cmd.test` (`bench --site miyano run-tests --app erp_ai`) trên 1f0b3f7: exit 0, `Ran 738 tests in 116.196s`, `OK`.
- `routing_rules` trong DB là JSON mặc định; `auto_assign_enabled` = 0; `validate_routing_config` chấp nhận.

## Quyết định của team-leader sau C2 (journal "quyết định 4 điểm")

1. `routing_rules` trống: bộ kiểm từ chối khi lưu (T9b, xong).
2. Mở rộng touchpoint T6 và T11: chấp nhận (ghi ở trên).
3. Khóa tiền tố rỗng `""`: T8 giữ bỏ qua; bộ kiểm từ chối khi lưu (T9b, xong).
4. 99 Has Role của tài khoản agent: ngoài FEAT-006.

## Đang build

Chặng 3 (`--decide`): T9b xong; kế tiếp T13 → T14 → T15 → T16 (MỘT dev mỗi lần), dừng ở checkpoint C3 rồi báo cáo.

## Nhật ký

- 2026-11-12 T1: dev lần 1 DESIGN_CONFLICT; người duyệt mở rộng touchpoint; dev lần 2 DONE; reviewer vòng 1 request-changes (3 major); dev sửa; vòng 2 approve; merge; 660 test OK.
- 2026-11-12 R1 (T3 ∥ T6): T6 DESIGN_CONFLICT (test T1 giả) → tech-lead mở rộng touchpoint 1 file; cả hai approve vòng 1.
- 2026-11-12 R2/R3 (T4 ∥ T5): hai dev song song làm `cmd.test` deadlock lẫn nhau; cả hai approve vòng 1; merge không xung đột; chuyển sang chạy từng dev một.
- 2026-11-12 T7, T2, T8: mỗi task request-changes vòng 1, approve vòng 2; đã merge; ghi tick và review-02/07/08 ở chặng 2.
- 2026-11-12 T9: vòng 1 request-changes (major STD-TEST-8: 5 hàng bộ kiểm không có ca); vòng 2 còn thiếu bảo vệ `default`/`prefixes` của `assignees`; vòng 3 approve. Nền nối tiếp 703 OK nhờ dev T9 chạy trước khi sửa.
- 2026-11-12 T10: dev DONE, reviewer approve vòng 1; merge a9e7e2e; 723 OK.
- 2026-11-12 T11: dev DESIGN_CONFLICT (`test_doctype_descriptions` ghim 22 trường); tech-lead mở rộng touchpoint 1 file và commit phần dở; dev sau DONE; reviewer approve vòng 1; reviewer nêu quyết định thiết kế "routing_rules trống" cần người chốt (review-11); merge 27d18fe; 728 OK.
- 2026-11-12 T12: reviewer vòng 1 request-changes (3 major: bảo vệ Task bị che, thiếu dòng mồi share, nghi cache meta); vòng 2 approve (finding cache được reviewer rút lại); merge 1f0b3f7; 738 OK.
- 2026-11-12 C2: migrate exit 0, ensure_setup lần hai không đổi gì, cmd.test 738 OK; dừng báo cáo.
- 2026-11-12 T9b: vòng 1 request-changes (major STD-ERR-3: thông báo trống nhắc tên hằng Python; minor: `.strip()` trên giá trị không phải chuỗi); vòng 2 approve; merge 4dc14d7; 744 OK.
