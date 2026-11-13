Feature: FEAT-004
Stage: design
Author-agent: designer
Date: 2026-11-13

# Design FEAT-004, phụ lục 3: remote là URL, lỗi đọc git ở kiểm sau, vòng import policy, `exit_code`, `finish`, chữ ký method
Bổ sung `design.md` và `design-addendum-2.md`, không viết lại. Nguồn: review-39, review-05, review-14, review-16; mã `team/FEAT-004` (`5e608a3`), `team/FEAT-004-task-39` (`8ff4278`), `team/FEAT-004-task-5` (`d62f6ec`). Tuân ADR-011 QĐ 2/3, ADR-012 QĐ 3/7, ADR-013 QĐ 5/6, ADR-022 QĐ 1/3/7/8. Không cần đổi ADR.

## QĐ-B1. Remote của nhánh là URL → "không theo", `""`/0 (T39)
**Quyết định.** Giữ design 3.2 bước 7 (chỉ `rev-parse @{upstream}`, không đọc `.git/config`). `branch.<n>.remote` là URL thì không có ref remote-tracking, git thoát 128 → không theo: `upstream_ref = ""`, `ahead_count = 0`, URL xuất hiện 0 lần. Mặt nạ `(remote không tên)` chỉ dùng khi `rev-parse` trả mã 0 mà chuỗi có `://` hoặc `@` (vd tên remote chứa `@`). Đúng AC-21 ("nếu nhánh theo một nhánh remote") và NFR-8. Mã `8ff4278` không đổi.
**Sửa:** design 3.2 bước 7 (thêm câu trên); design 8.1 dòng AC-21 `test_upstream_with_url_like_name_is_masked` (design.md:920) đổi mô tả thành "tên remote chứa `@` → `(remote không tên)`", thêm dòng AC-21/NFR-8 `erp_ai/agent/tools/test_source.py::test_branch_remote_set_to_url_never_leaks_it` ("`branch.<n>.remote` là URL có token giả → `""`/0, URL và token 0 lần"). **Task:** T39 sửa câu Returns cuối thành "`branch.<n>.remote` là URL → không theo, `""`/0, URL không xuất hiện"; merge được nguyên mã. **Test thêm:** không (đã có trong `8ff4278`).

## QĐ-B2. Lỗi đọc git sau khi commit có thể đã thành: không bao giờ trả lại file (T19, T45, T20, T47)
**Hợp đồng hàm đọc (design 3.2, ghi chú chữ ký, đúng mã T39):** `git_head` → `None` khi chưa có commit, git lỗi hoặc quá giờ; `git_commit_summary` ném `RuntimeError(GIT_ERROR …)` khi git lỗi/quá giờ/đầu ra lạ; `git_blob` → `None` chỉ khi đường dẫn không có trong cây (git thoát 128), lỗi khác ném `RuntimeError`; `git_is_ancestor` → `None` khi lỗi.
**Quyết định.** Chia theo điều đã biết, áp như nhau cho áp dụng (4.3) và hoàn tác (4.4 bước 6):
1. **Đã biết commit của bot có** (lệnh commit thoát 0, hoặc HEAD dịch và `author_email == BOT_GIT_EMAIL`): từ lúc này cờ `committed = True`, hàm trả lại (3.6) không bao giờ được gọi. Ở kiểm sau, `git_commit_summary` hoặc `git_blob` ném `RuntimeError`, hoặc `git_is_ancestor` trả `None` → coi là kiểm sau sai (ADR-022 QĐ 1 bước 5): `finish(→ Lỗi, step="fail", reason=GIT_COMMIT_MISMATCH, fields={"apply_commit_sha"|"undo_commit_sha": sha})`, không sửa lịch sử. `sha = s.commit` nếu đã đọc được `s`; không thì gọi `git_head(repo)` một lần, lưu khi khác `None` và khác `old_head`; còn lại không lưu.
2. **Chưa biết commit có hay của ai:** lệnh commit lỗi/quá giờ và `git_head(repo) is None`; hoặc HEAD dịch mà `git_commit_summary` ném → `finish(→ Lỗi, step="fail", reason=GIT_ERROR)`, **không** trả lại (file có thể đã nằm trong commit của bot), không lưu mã commit. Chỉ trả lại khi chứng minh được `git_head == old_head` (D-17 giữ nguyên).
3. Trong hàm trả lại (3.6), `git_head` trả `None` → không bằng `old_head` → `GIT_RESTORE_FAILED` (như hiện có).
4. Design 4.3 bước 5: `RuntimeError` của 3 hàm trên được bắt tường minh ở bước 3.4/3.5 (không rơi vào nhánh exception chung). Exception bất ngờ khác: chạy trả lại **chỉ khi** `committed is False`; `committed is True` → chỉ `finish(→ Lỗi, reason=type(exc).__name__)`, kèm `fields` mã commit nếu đã biết.
**Sửa:** design 3.2 (ghi chú chữ ký 4 hàm), 4.3 bước 3.4, 3.5, 5; 4.4 bước 6; 4.5 thêm dòng "commit không rõ (`GIT_ERROR` sau lệnh commit)": file đích mang `content_after`, có thể chưa commit; người xem `git log -1`, `git status`. **Task:** T19 (kiểm sau ở nhánh thành công: mục 1), T45 (mục 1–4 phía áp dụng), T20 (kiểm sau hoàn tác: mục 1), T47 (mục 1–3 phía hoàn tác). Không thêm touchpoint. T39 không đổi.
**Test thêm (`erp_ai/agent/changes/test_apply_job.py`):**
- T19 `test_postcheck_unreadable_keeps_commit_and_fails` (subTest `git_commit_summary` ném, `git_blob` ném, `git_is_ancestor` → `None`: file = `content_after`, HEAD = commit bot, `Lỗi` `GIT_COMMIT_MISMATCH`, `apply_commit_sha` có, 0 lần ghi trả lại, 1 dòng `fail`);
- T45 `test_commit_failed_and_head_unreadable_fails_without_restore` (stub `git_commit_only` mã 1 và `git_head` → `None`: `Lỗi` `GIT_ERROR`, file không bị ghi lại, 0 `git_unstage_new`, không `apply_commit_sha`);
- T45 `test_head_moved_and_summary_unreadable_fails_without_restore` (`GIT_ERROR`, không trả lại, không mã commit);
- T45 `test_exception_after_commit_landed_does_not_restore` (stub ném `KeyError` sau commit thoát 0: file = `content_after`, `Lỗi` `KeyError`, `apply_commit_sha` có);
- T47 `test_undo_postcheck_unreadable_keeps_commit_and_fails` (như T19, phía hoàn tác, `undo_commit_sha`).

## QĐ-B3. Cắt vòng import policy → tools.source → tools.read → policy: (b) truyền gốc `apps/` vào policy (T5, T6)
**Quyết định.** Chọn (b) dạng hẹp: `policy` không import gì trong `erp_ai.agent.tools`. Lý do: 0 file đã merge phải đổi; (a) phải sửa `read.py`, `source.py`, `registry.py` đã merge. (c) import trong thân hàm: không (STD-DESIGN-6).
- Chữ ký mới (design 3.6): `policy.validate_change_apps(settings, apps_root: str) -> None`. Giữ nguyên 3 câu, thứ tự (mọi dòng tên sai/`erp_ai` trước, rồi thư mục), kiểm `os.path.isdir(os.path.join(apps_root, name))` vẫn ở policy. Chỉ policy đọc `code_change_apps` (ADR-011 Ràng buộc giữ).
- `ERPAISetting.validate` gọi `policy.validate_change_apps(self, source.get_source_root())` (`from erp_ai.agent.tools import source`). `source.get_source_root` vẫn là hàm gốc duy nhất (ADR-022 QĐ 8; `test_apps_root_single_function` giữ xanh).
- Luật mới 8.2: dòng `LAYER_RULES` `("erp_ai.agent.policy", ("erp_ai.agent.tools",), "STD-DESIGN-6: policy là tầng dưới của tools, không import ngược")`.
**Sửa:** design 3.6 (dòng `policy.validate_change_apps`), 7 (dòng `erp_ai_setting.py`: thêm import `source`), 8.2 (luật trên + test tiến trình mới). **Task:** T5 (bỏ `from erp_ai.agent.tools import source`; thêm tham số; test cũ chỉ đổi cách gọi, không đổi assertion; `test_architecture.py` đã trong `files:`). T6 (Returns: truyền `source.get_source_root()`). Không thêm touchpoint. Gỡ chặn T6, T18, T29.
**Test thêm:**
- T5 `erp_ai/agent/test_policy.py::test_validate_change_apps_uses_given_root` (2 thư mục tạm; chỉ thư mục truyền vào được dùng; không patch `get_source_root`);
- T5 `erp_ai/tests/test_architecture.py::test_agent_modules_import_alone_in_fresh_process` (subTest `erp_ai.agent.policy`, `erp_ai.agent.tools.read`, `erp_ai.agent.tools.source`, `erp_ai.agent.tools.registry`, `erp_ai.erp_ai_agent.doctype.erp_ai_setting.erp_ai_setting`: mỗi module `subprocess.run([sys.executable, "-c", "import <m>"])` mã 0; đỏ trên `d62f6ec` với `tools.read`);
- T5 `erp_ai/tests/test_architecture.py::test_layer_imports_catches_policy_importing_tools` (mã giả `policy.py` import `erp_ai.agent.tools.source` → bị bắt);
- T6 `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::test_validate_checks_dirs_under_source_root` (patch `source.get_source_root` về thư mục tạm có `apps/myapp` → lưu được; không có → câu `Không có thư mục apps/<x>`).

## QĐ-B4. `exit_code` không có giá trị: đề xuất lưu 0 và ẩn ô, nhật ký lưu `null` (trước T21)
**Quyết định.** Không đổi kiểu cột (Int của Frappe 15 là `NOT NULL DEFAULT 0`; đổi sang Data là đổi schema đã merge không cần thiết). Sửa QĐ-A3 mục 2 của phụ lục 2: "`exit_code` rỗng" → đề xuất `exit_code = 0`, dòng `fail` có `value_after.exit_code = null` (đúng mã `finish` T14). Form: `exit_code` có `depends_on = eval:doc.change_status=="Đã áp dụng" || doc.exit_code`. Lệnh luôn thoát 0 khi `Đã áp dụng`, và lỗi có mã thật (≠ 0, kể cả 124/137/127) vẫn hiện, nên ô ẩn đúng khi không có mã (hết ngân sách, `TimeoutExpired`, chưa chạy).
**Sửa:** phụ lục 2 QĐ-A3 mục 2; design 2.1 (ghi chú `exit_code`), 3.3 bố cục hàng 6 cột "Hiện khi". **Task:** T21 + 2 touchpoint `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json`, `.../test_erp_ai_change_proposal.py` (cần `cmd.migrate`); tech-lead có thể tách task riêng.
**Test thêm:** T21 `test_command_without_budget_fails_as_timeout_without_subprocess` đổi kiểm thành `exit_code == 0` trên đề xuất và `value_after.exit_code is None`; `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py::test_exit_code_hidden_when_unknown` (đọc JSON: `depends_on` đúng chuỗi trên).

## QĐ-B5. `finish` có `before=`/`after=`; nơi gọi điền `value_after.commit` (T19, T45, T20, T47)
**Quyết định.** Design 3.5 thay chữ ký bằng đúng mã T14: `finish(name, expected, new_status, *, step, actor, reason=None, result=None, fields=None, before=None, after=None) -> bool`; `before`/`after` chuyển nguyên vào `value_before`/`value_after` của dòng log. `finish` không tự suy `value_after` (không đổi mã đã merge). `apply_job` là nơi duy nhất điền: mọi lời gọi `finish` có `fields` chứa `apply_commit_sha`/`undo_commit_sha` phải truyền `after={"sha256": sha256_of(full), "commit": <cùng mã>, "branch": <nhánh đọc được hoặc None>}` và `before={"sha256": <hash trước>, "head": old_head}`. Không có mã commit → `after` không có khóa `commit`.
**Sửa:** design 3.5 (chữ ký), 2.5 (câu "dòng `fail` có `apply_commit_sha`…": thêm "do `apply_job` truyền qua `after=`"). **Task:** T19, T45, T20, T47 (Returns ghi rõ `after=` ở nhánh `fail` có mã commit). Không thêm touchpoint.
**Test thêm:** T45 `test_fail_row_with_commit_sha_carries_value_after_commit` (subTest mismatch áp dụng, `RuntimeError` kiểm sau: `value_after.commit == apply_commit_sha`); T47 cùng tên phía hoàn tác (`undo_commit_sha`).

## QĐ-B6. Method HTTP không chú thích kiểu: `approve(name=None)`, `reject(name=None)`, `undo(name=None)`
**Quyết định.** Bỏ `: str` ở design 3.3. Lý do: Frappe 15 bọc hàm whitelist bằng `validate_argument_types`; có chú thích thì 123/None/list bị trả `FrappeTypeError` (417) trước thân hàm, trái dòng lỗi 404. Thêm mặc định `None`: thiếu `name` → cùng `DoesNotExistError` 404 (hiện là `TypeError` 500, review-16 minor 3). Bảng lỗi 3.3 dòng 404 đổi "Khi nào" thành "`name` thiếu, không phải chuỗi hoặc không tồn tại". Thứ tự kiểm giữ: role → name → chuyển trạng thái → xếp job.
**Sửa:** design 3.3 (bảng method, bảng lỗi). **Task:** T16 đã merge: tech-lead chèn task nhỏ (`/team:plan --insert`) trên `erp_ai_change_proposal.py` + test của nó; Returns T16 đổi chữ ký trong tasks.md.
**Test thêm:** `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py::test_methods_missing_name_is_not_found` (gọi qua lớp bọc whitelist không có `name`, cả 3 method: `DoesNotExistError`, DB/log/job không đổi).

## Assumptions decided by the team
- QĐ-B1: nhánh theo remote URL hiện như "không theo" trên form; bot không push nên số đi trước chỉ để thông tin.
- QĐ-B2: `GIT_ERROR` sau lệnh commit để lại file `content_after` có thể chưa commit; chọn vậy vì ghi đè một file đã commit tệ hơn (người đối soát theo 4.5).
- Ngoài phạm vi phụ lục này: chữ hộp thoại xác nhận (review-17), `commit_message` của đề xuất lệnh bench (review-49). Không có câu hỏi nghiệp vụ.
