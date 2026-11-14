Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 01 — CHG-002 T1

- Diff: `git diff dd444ad..f6f5086` (nhánh `team/CHG-002-task-1`, 2 commit `f8b4e62`, `f6f5086`; đã merge vào `team/CHG-002` ở `fd69e5f`)
- Vòng: 1 (max_rework = 3). Dev được gọi 2 lần trước khi review: lần 1 dừng `DESIGN_CONFLICT` (4 test cũ ghim hình dạng), lần 2 sửa 4 test theo `design-addendum-2.md`.
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | 0 blocker, 0 major | — |

minor | — | — | 7 điểm nhỏ (xem mục deferred) | tùy dev

## Review checklist (10)
1. Đạt. AC-36 phần khung: `test_one_edit_block_proposed_approved_applied_one_commit` kiểm cả đường (1 đề xuất `Chờ duyệt` có 1 dòng con đúng giá trị và hash, trường vô hướng rỗng, nhãn commit là đường dẫn của mục, 1 comment, HEAD không đổi trước khi duyệt, `approve` xếp đúng 1 job, sau job `Đã áp dụng`, byte file đúng, commit chỉ chứa 1 đường dẫn, cây sạch). §2.1, §2.2, khối hằng, `FileOp` 7 trường frozen, ba hàm `block.py`, dấu §2.4, `required=["reason"]` khớp Returns. Phần thừa duy nhất: vài hằng tạo sớm (minor 2).
2. Đạt. 14/14 file là touchpoint; 3 file mới nằm dưới `erp_ai/`.
3. Đạt, kèm minor 1. Có đầu ra đỏ của cả hai lần gọi dev; không skip/xfail.
4. Đạt. Bốn lần sửa test theo L-1 và STD-TEST-5: vẫn so bằng, không nới thành tập con hay `>=`, assertion không đổi giữ nguyên từng byte; test dùng `GitSandbox`, tự rollback.
5. Đạt. Mục lồng trong `changes[]` được handler kiểm; đường dẫn không phải chuỗi bị bộ chặn từ chối; không thêm lời gọi ngoài.
6. Đạt. Comment escape đường dẫn; agent vẫn ghi qua đúng một `insert` có guard (RQ-1: 1 `.insert(`, 1 `allow_agent_write()`); kiểm vai trò và duyệt không đổi; không bí mật, không chạm `protected_paths`.
7. Đạt. Trường và DocType chỉ thêm; dấu dạng cũ không đổi (rẽ theo `is_block`); đổi hợp đồng tool theo A2-2.
8. Đạt. Tên theo profile; không mã chết.
9. Đạt. Không thêm phụ thuộc.
10. Đạt, kèm minor 3. Tiêu đề commit `type(scope): … (CHG-002)`, không dòng AI, đủ 4 dòng `test-shape:`.

## Đối chiếu L-1 (4 dòng `test-shape:` với phần sửa)
- `test_select_options_match_constants`: vẫn so bằng tập; danh sách lựa chọn so với cả chữ lẫn hằng; `default` rỗng. Khớp.
- `test_content_fields_are_code_and_read_only`: `CODE_FIELDS | BLOCK_CODE_FIELDS`, 41 trường (35 + 6), `options == "JSON"`, trường Table và Datetime; vòng `read_only` không đổi. Khớp.
- `test_form_layout_git_sections`: chỉ `FIELD_ORDER` đổi và bằng `field_order` của JSON. Khớp.
- `test_edit_errors_create_nothing`: kỳ vọng `…: edits`; thêm ca `{path, replace, reason}` → `…: find` (bỏ vòng `LEGACY_EDIT_KEYS` thì handler ném `KeyError`, nên ca này đỏ được). Khớp.

## Không kiểm được từ diff, tech-lead đã xử lý
- Lint: `cmd.lint` (`pre-commit run --all-files`) trên `team/CHG-002` @ `fd69e5f`: 12 hook đều `Passed`.
- Cả app và migrate: xem dòng progress của T1 trong `tasks.md` (`cmd.migrate` + `cmd.test` trong một lần giữ khóa, trên `fd69e5f`; cây của `fd69e5f` trùng cây của `f6f5086`, `aa89ee1`).
- Cửa sổ hoàn tác khối trước khi task hoàn tác (T39, T40) merge: `_undo_code` nhận `file_path=None`, dừng ở `PATH_INVALID`, không ghi gì, nhưng đề xuất chuyển `Đã áp dụng` → `Lỗi`. Không phải thiếu sót của T1: nhánh `team/CHG-002` chỉ vào `develop` sau T51, không ai tạo đề xuất khối thật trước đó; AC-42 do T39, T40 phủ.
- Reviewer không chạy test.

## deferred
Bảy điểm minor của vòng 1, không chặn merge; task nêu bên cạnh thay thế phần liên quan:
1. STD-TEST-8: các nhánh từ chối tạm của `_propose_block` (`BLOCK_SHAPE`, `BLOCK_EMPTY`, `OP_UNKNOWN`, `OP_FIELDS`) và của `_apply_block` (`STORED_HASH_MISMATCH`) chưa có test → T12, T26, T27 (phía tool), T33 (bỏ `_apply_block` giả).
2. STD-DESIGN-1: `BLOCK_EMPTY`, `OP_UNKNOWN`, `OP_FIELDS` đã được tạo ở T1 dù Returns của T12 liệt kê chúng → báo cho dev T12 là hằng đã có.
3. STD-GIT-2: `f8b4e62` đứng riêng còn 4 test đỏ, `f6f5086` làm xanh; addendum-2 cho phép hai commit.
4. STD-ERR-2: khối nhiều mục `edit` hoặc hai app được nhận lúc đề xuất, job từ chối bằng `OP_UNKNOWN` (sai lý do, 0 byte ghi) → T12, T27.
5. STD-DOC-7: mô tả tool `propose_file_change` còn nói `path/find/replace`; enum đã có `create/delete/rename` mà T1 từ chối → T26..T29.
6. STD-TEST-2: chưa test nào đỏ nếu bỏ dòng con khỏi dấu khối (§2.4) → T42 (`TestOneApproval::test_row_edited_in_db_after_approval_refused_file_unchanged`).
7. STD-STYLE-5: dòng `test-shape:` thứ tư có hai mũi tên, khó đọc cũ → mới.
