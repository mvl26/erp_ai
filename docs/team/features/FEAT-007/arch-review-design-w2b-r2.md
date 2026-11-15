Feature: FEAT-007
Stage: architect
Author-agent: architect
Date: 2026-11-14
Approved-by:
<!-- G2b không áp dụng (team.py: chỉ G5). Để trống. -->

# Rà soát kiến trúc vòng 2: hai file sửa của design đợt 2b (U7a vòng sửa 2, U7b-U8 vòng sửa 1), FEAT-007

**Phán quyết tổng: approve có điều kiện cho cả hai file sửa; không có design-defect; không có ADR mới.**
- Mọi finding của `arch-review-design-w2b.md` (J-1..J-6, minor (a)–(f)) và mọi phán quyết (1)–(9) đã được giải.
- Các sửa sinh ra bốn finding mới L-1..L-4 (major). Mỗi finding có đúng một cách sửa, không còn chỗ cho designer chọn, nên không mở vòng design thứ ba. Plan đợt 2 mang chúng thành điều kiện C-4..C-7 (mục 6). Tech-lead chép nguyên chữ vào task.
- L-1 cần thêm một câu vào ADR-035 QĐ 6. ADR-035 vẫn `proposed`; architect thêm câu đó ở lời gọi kế, trước khi người duyệt ADR-035 (mục 7).

Đọc file này **sau** `arch-review-design-w2b.md`. Ở chỗ khác nhau, file này thắng cả hai file sửa.

**Đánh số.** Dòng đầu của w2b (`arch-review-design-w2b.md:12`) gọi nhầm ba major là J-4, J-5, J-6. Bảng finding (`:70-75`) mới đúng: J-3 danh sách, J-4 tool đọc Setting, J-5 Custom Field, J-6 minor import `authority`. File này theo bảng, như designer U7b đã làm (`design-addendum-2-U7b-U8-fixes.md:14`).

## Căn cứ (đọc trực tiếp ngày 2026-11-14; đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Cờ "đã commit" của J-1 có dựa được vào `after_commit` không | Được. `commit()` chạy `after_commit.run()` sau `commit` + `begin()`. `rollback()` toàn phần gọi `reset()`. `rollback(save_point=…)` không đụng callback | `apps/frappe/frappe/database/database.py:1187-1215` |
| Patch `validate_fields_for_doctype` có ăn không | Có. Hàm được import trong thân `on_update` (`:209`), gọi ở `:211`, trước `updatedb` (`:216`) | `apps/frappe/frappe/custom/doctype/custom_field/custom_field.py:206-216` |
| Test "Từ chối → 0 job" nằm đâu | `team/FEAT-004`: `erp_ai/test_change_decision.py:239` `test_post_reject_zero_jobs` (`self.jobs() == []` ở `:244`). `develop`: không có tên đó. Test cùng nghĩa là `:79` `test_reject_link_rejects_without_a_job` (`:83`). File đang có sửa chưa commit của CHG-001 | worktree `feat-004`; `git diff erp_ai/test_change_decision.py` |
| `STATE_FIELDS` có bị test ghim không | Có. `erp_ai/agent/changes/test_transitions.py:41-52` `STATE_FIELDS_EXPECTED`; `:175` `assertEqual(transitions.STATE_FIELDS, STATE_FIELDS_EXPECTED)`; `:198` lặp `STATE_FIELDS_EXPECTED[1:]` trong test `prepare_new` | worktree `feat-004` và `develop` |
| ADR-023 về job | Ở đầu `_run` của job, cho cả áp dụng và hoàn tác, **trước mọi kiểm khác**: người thực hiện đã lưu không thuộc `NEVER_AUTHORITY` và vẫn có `ERP AI Instructor`, user phiên của job trùng người đó. Sai → `Lỗi`. Request GET không commit, nên `rollback` xóa hàng `after_commit` | `docs/team/adr/ADR-023.md:36`, `:19` |
| FEAT-004 nói gì về Từ chối | "mở Từ chối là không đổi gì" (không có AC nào đếm job khi Từ chối) | `docs/team/features/FEAT-004/spec.md:283` |
| FEAT-007 AC-33 | "Sau Từ chối: không ghi, có log và comment" | `docs/team/features/FEAT-007/spec.md:199` |
| Wave 2 cắt từ đâu | U7a "sau FEAT-004": nhánh cắt hoặc rebase từ `develop` sau khi `team/FEAT-004` merge | `arch-impact.md:168`; `plan.md:21` |
| Tiến độ | `team/FEAT-007` mới tới T1 của đợt 0 (`19e92a7`). U1 chưa build | `git log team/FEAT-007` |
| `threshold` trong mã hiện có | 0 dòng ngoài test (`grep -rn threshold erp_ai --include=*.py`) | `develop` |

## 1. Phán quyết từng file

| File | Phán quyết | Lý do |
|---|---|---|
| `design-addendum-2-U7a-fixes-2.md` | **approve có điều kiện** (C-4, C-5, C-8, C-10, C-11) | J-1: Sửa 1 phân biệt bằng commit thật (`:44-52`), và cơ chế khớp mã Frappe. J-2 / (7): job đăng comment, chống lặp bằng trường trạng thái có khóa dòng (`:77-136`). (6): hai hàm có từ đầu (`:144-162`). (9): câu `:286` sửa đúng (`:168`). Còn L-1 (thứ tự nhánh Từ chối so với kiểm lại của ADR-023) và L-2 (test FEAT-004 ghim `STATE_FIELDS` chưa được kê) |
| `design-addendum-2-U7b-U8-fixes.md` | **approve có điều kiện** (C-6, C-7, C-8, C-9) | J-3: một định nghĩa "giao mở", test danh sách bằng hook trên 5 đường danh sách (`:38-95`). J-4: tool chỉ đọc `ctx`, một phép so ở `policy` (`:99-168`). J-5: vế tự commit, test giữ savepoint (`:172-199`). J-6: ngăn đi qua controller (`:249-281`). (4), (5), (9), minor (a)–(e) đúng chữ. Còn L-3 (khóa `changes` không có trong `record_summary`) và L-4 (luật AST "một phép so ngưỡng" bắt cả `is not None` của chính vế 4) |

## 2. Từng finding và phán quyết của w2b

| Mục w2b | Trạng thái | Giải bởi (file:dòng) |
|---|---|---|
| J-1 (major, cờ "đã commit" suy từ `exists`) | **Giải** | U7a-fixes-2 Sửa 1.1 `:44-52`, test `:64-68`, A-U7a-15 `:203` |
| J-2 (major, AC-33 comment sau Từ chối) | **Giải**, kèm L-1, L-2 | U7a: Sửa 2 `:73-140`. U7b: Sửa 8 `:303-311` |
| J-3 (major, danh sách rộng hơn hook) | **Giải**, kèm C-8 | U7b-fixes Sửa 1 `:38-95`, Sửa 5 `:233-245` |
| J-4 (major, tool đọc Setting, so ngưỡng lần hai) | **Giải**, kèm L-4 | U7b-fixes Sửa 2 `:99-168`, Sửa 7 `:285-299` |
| J-5 (major, Custom Field "Tự làm" commit giữa lượt) | **Giải** | U7b-fixes Sửa 3 `:172-199`; U7a-fixes-2 Sửa 1.3 `:58` |
| J-6 (minor, ngăn import `authority`) | **Giải**, kèm L-3 | U7b-fixes Sửa 6 `:249-281` |
| minor (a) `NOT_ELIGIBLE`, N-6, N-7 | **Giải** | U7b-fixes Sửa 9 `:319` |
| minor (b) N-1 thuộc U1 đợt 1 | **Giải** | U7b-fixes `:320` |
| minor (c) `catalog_approvals` không là tool | **Giải** | U7b-fixes `:321` |
| minor (d) option `.js` | **Giải** | U7b-fixes Sửa 4 `:217`, `:228` |
| minor (e) từ cấm AC-9 | **Giải** | U7b-fixes `:218` |
| minor (f) câu `:286` | **Giải** | U7a-fixes-2 Sửa 4 `:168` |
| Phán quyết (1) DocPerm `Agent` + hai hook cùng commit | **Giải** | U7b-fixes `:78-81`, `:94`, `:355` (i) |
| Phán quyết (2) tập đọc = "được giao" | **Giải** | U7b-fixes `:45-58`, `:62-71`, `:90` |
| Phán quyết (3) bit `proposal_one_step` | **Giải** | U7b-fixes `:266-268` |
| Phán quyết (4) U8 một commit | **Giải** | U7b-fixes Sửa 4 `:207-223` |
| Phán quyết (5) `PANEL_METHODS`, `hooks.py` | **Giải** | U7b-fixes Sửa 5 `:237-245` |
| Phán quyết (6) `_post_comment`, `record_summary` | **Giải** | U7a-fixes-2 Sửa 3 `:144-162`; U7b-fixes `:183`, `:261` |
| Phán quyết (7) comment Từ chối trong job | **Giải**, kèm L-1, L-2 | U7a-fixes-2 `:85-121`; U7b-fixes `:307-310` |
| Phán quyết (8) hành động tự commit không "Tự làm" | **Giải**. Câu nghiệp vụ "Custom Field luôn cần duyệt" vẫn mở, không chặn | U7b-fixes `:143`, `:176-186`, `:194-195` |
| Phán quyết (9) chữ `:229-231` và `:286` | **Giải** | U7b-fixes Sửa 7; U7a-fixes-2 Sửa 4 |
| Phán quyết (10) ADR-035 | Không việc của designer. Cần thêm một câu do L-1 (mục 7) | — |

## 3. Hai file sửa có khớp nhau không

| Điểm | U7a-fixes-2 | U7b-U8-fixes | Khớp |
|---|---|---|---|
| Số job khi Từ chối | `reject` xếp **1** job `enqueue_change_job(name, "apply")` (`:91`); test `:127`, `:131` | reject → **1** job, đích không đổi; `decide_proposal` không enqueue (`:307-309`) | **Khớp** |
| Comment sau Từ chối | job, `_post_result`, cờ `rejection_comment_posted` (`:97-113`) | job của U7a; U7b chỉ test đường ngăn, chạy lại → 0 (`:310`); không chạm `transitions.py`, `apply_job.py`, `result_comment.py` (`:353`) | **Khớp** |
| `rejection_comment_posted` | trường trạng thái, chỉ `transitions.py` ghi (`:77`, `:85`) | không nhắc, không chạm. Sửa JSON của U7b chỉ thêm DocPerm, đi sau U7a | **Khớp** (thứ tự U7a → U7b của w2b mục 5) |
| `authority.open_assignment_condition` | không nhắc. `_open_assignment`, `is_assigned` của U7a không đổi | thêm cạnh `is_assigned`, chép **đúng** biểu thức sắp ToDo của U7a (`:52`, `:58`) | **Khớp có điều kiện**: U7a phải ghim biểu thức sắp có khóa phụ (C-8) |
| `policy.meets_confidence` | không nhắc | U7b thêm, đổi thân `is_below_confidence` của U1 (`:106-110`) | **Khớp** (không đụng U7a); chủ xem phán quyết (2) |
| `ToolContext.threshold_pct`, `streak_required` | không nhắc | U7b, mặc định `None`, runner bước (e) (`:115-129`) | **Khớp** |
| `IMPLICIT_COMMIT_ACTIONS` | giữ tên, giá trị (`:42`); ghi chú U7b (`:58`) | import, không chép (`:176`) | **Khớp** |
| `_post_comment(ctx, html) -> str` | `:148` | gọi cho `AUTO_DONE_COMMENT` (`:183`) | **Khớp** |
| `record_summary(doc) -> dict` | tập khóa cố định, có test ghim (`:152`, `:162`) | `panel_summary = {**record_summary(doc), "can_decide"}` (`:257`), nhưng ngăn đọc `s["changes"]` (`:265`) | **Lệch**: L-3 |

## 4. Finding mới

Định dạng: `severity | STD | ADR bị phá | file:line | mô tả | sửa`.

| # | severity | STD | ADR bị phá | file:line | mô tả | sửa |
|---|---|---|---|---|---|---|
| L-1 | major | STD-DESIGN-2 | ADR-023 (`:36`, kiểm lại người duyệt ở đầu `_run`); ADR-035 QĐ 6 | `design-addendum-2-U7a-fixes-2.md:97` | Nhánh `Đã từ chối` đặt "ngay sau khi đọc `row`" trong `_locked_run`. Nhưng ADR-023 đặt phép kiểm lại người duyệt ở đầu `_run`, "trước mọi kiểm khác", cho mọi job `apply`, và job Từ chối lại dùng `action="apply"`. Người từ chối là agent Helpdesk được giao (được quyết đề xuất bản ghi theo ADR-031 QĐ 5), hoặc Instructor bị thu role trước khi job chạy, thì không qua được kiểm đó. Job khi ấy đẩy `Đã từ chối` sang `Lỗi` (hoặc ném `InvalidTransition`) và comment AC-33 không bao giờ được đăng | Nhánh `Đã từ chối` (với `action == ACTION_APPLY`) là **bước đầu tiên** của job: trước phép kiểm lại của ADR-023, trước `_recheck` của FEAT-004, trước khóa. Lý do: job này không ghi đích, chỉ đăng comment dưới tài khoản agent. Thêm test `TA::TestRejectComment::test_reject_job_skips_decider_recheck`, có subTest "người từ chối là agent Helpdesk được giao (đề xuất bản ghi)" và "Instructor bị thu role trước khi job chạy": +1 comment, trạng thái vẫn `Đã từ chối`, 0 Error Log của phép kiểm lại. ADR-035 QĐ 6 thêm một câu (mục 7) |
| L-2 | major | STD-DESIGN-1 | ADR-031 Ràng buộc 6 (không phá, chỉ thiếu touchpoint) | `design-addendum-2-U7a-fixes-2.md:77`, `:184` | Nối `rejection_comment_posted` vào `transitions.STATE_FIELDS` làm đỏ `test_transitions.py::TestTransitionsBasics::test_state_fields_are_the_design_state_group` (`:175`, test FEAT-004 ghim `STATE_FIELDS_EXPECTED` `:41-52`). Nó cũng đổi nghĩa của `test_prepare_new_forces_pending_and_clears_state_fields` (`:198`). Design không kê hai test này, nên dev sẽ dừng `DESIGN_CONFLICT` | U7a, cùng commit với trường: nối `"rejection_comment_posted"` vào cuối `STATE_FIELDS_EXPECTED` và đặt khóa đó bằng `1` trong `STATE_VALUES`. `prepare_new` đưa cờ về rỗng/0 như mọi trường trạng thái (đề xuất sao chép không mang cờ). Không sửa assertion nào khác. Áp phán quyết (1) cho file này |
| L-3 | major | STD-DESIGN-1 | ADR-035 QĐ 4 (dữ liệu ngăn qua controller; không phá, chỉ lệch hợp đồng) | `design-addendum-2-U7b-U8-fixes.md:257`, `:265`; `design-addendum-2-U7a-fixes-2.md:152` | Ngăn đọc `s["changes"]`, nhưng `record_summary` của U7a không có khóa `changes`, và tập khóa của nó bị test `TP::TestRecordSummary::test_keys_and_editable_args` ghim. Hai task cùng tuân hai file vẫn xung đột: hoặc `KeyError`, hoặc U7b sửa hợp đồng U7a | `panel_summary` (U7b) tự dựng `changes` và `edit_fields` theo bảng `:116-123` của addendum U7b, từ các khóa có sẵn của `record_summary` (`editable_args`, `target_*`, `catalog_action`). `record_summary` không đổi chữ ký và tập khóa. `TP::TestPanelSummary::test_can_decide_matches_decider` khẳng định tập khóa = khóa `record_summary` ∪ {`changes`, `can_decide`} (∪ {`edit_fields`} khi `can_decide`) |
| L-4 | major | STD-DESIGN-2 | ADR-030 Ràng buộc 4 (cách thi hành) | `design-addendum-2-U7b-U8-fixes.md:168`, `:145` | `test_single_threshold_compare` coi mọi `ast.Compare` có toán hạng chứa `threshold` là phép so ngưỡng. Vế 4 `ctx.threshold_pct is not None` ở `catalog_tools.py` là một `Compare`, nên test đỏ ngay trên chính vị từ của U7b. Cách lách dễ thấy (loại `catalog_tools.py` ra) thì làm luật vô nghĩa | Luật chỉ bắt `Compare` có toán tử thứ tự (`Lt`, `LtE`, `Gt`, `GtE`) với một toán hạng là tên hoặc thuộc tính chứa `threshold` hoặc `confidence_pct`. Phép đó chỉ được nằm trong `policy.meets_confidence`. `Is`, `IsNot`, `Eq` với `None` không tính |

`minor | — | — | 4 điểm nhỏ: (a) test_post_reject_zero_jobs giữ tên mà khẳng định 1 job (STD-NAME-6): đổi tên theo phán quyết (1); (b) U7a-fixes-2 :79 câu đối soát nên trừ cả đề xuất có job đang chạy, không chỉ đang chờ; (c) U7b-fixes :92 nên thêm ca hai ToDo cùng creation để ghim khóa phụ của C-8; (d) U7b-fixes :154 logger "streak=-" khi vế 6 chưa chạy: giữ, nhưng ghi why trước streak đúng thứ tự trong test | dev's call`

## 5. Phán quyết (1)–(3)

**(1) U7a sửa test "Từ chối → 0 job" của FEAT-004. Chấp nhận. Chủ: U7a, đợt 2, cùng commit với `reject` xếp job.**
- Căn cứ STD-TEST-5: spec đổi thật. FEAT-007 AC-33 (`spec.md:199`) và ADR-035 QĐ 6 đổi hành vi Từ chối của cả ba đường. FEAT-004 không có AC nào đếm job khi Từ chối. Câu "mở Từ chối là không đổi gì" (`FEAT-004/spec.md:283`) vẫn đúng với đích. Comment là yêu cầu của spec mới hơn, đã duyệt. Đây không phải quyết định nghiệp vụ của architect.
- Điều kiện trước: `team/FEAT-004` và CHG-001 đã vào `develop`, và `team/FEAT-007` đã rebase (`arch-impact.md:168`). Lý do: trên đường GET cũ, request không commit nên `rollback` xóa hàng `after_commit`, và job `enqueue_after_commit` bị mất (`ADR-023.md:19`). Chưa merge thì task U7a này **chờ**, không làm trên `develop` hôm nay.
- Phạm vi theo **hành vi**, không theo tên. Lúc bắt đầu task, dev grep trên nền đã rebase mọi test khẳng định 0 job hoặc `enqueue` không được gọi sau Từ chối, trong `erp_ai/test_change_decision.py`, `test_erp_ai_change_proposal.py`, `agent/tools/test_propose_change.py`, rồi dán danh sách vào báo cáo task. Hôm nay danh sách gồm `team/FEAT-004` `test_change_decision.py:239` và `develop` `:79` (CHG-001 có thể đổi tên). Cộng `test_transitions.py` theo L-2.
- Chỉ sửa assertion số job: 0 → 1 job `RUN_CHANGE`, `action="apply"`, trạng thái lúc enqueue `Đã từ chối`. Thêm "0 comment trong request". Mọi assertion khác giữ.
- Đổi tên test cho đúng nghĩa (ví dụ `test_post_reject_enqueues_one_result_job`). Một dòng journal FEAT-007 ghi tên cũ → tên mới.
- Không sửa file nào trong `docs/team/features/FEAT-004/`. Commit theo STD-NAME-5 với `(FEAT-007)`. Chạy `cmd.test_one` cho từng file test đã sửa trước merge (K-5).

**(2) `policy.meets_confidence` và hai trường `ToolContext`. Chủ: U7b, đợt 2. Không chuyển về U1.**
- U1 sở hữu hợp đồng `is_below_confidence(confidence_pct, threshold, *, has_instructor, act_now)` (`design-addendum-1-U1.md:116`): chữ ký và hành vi. U7b giữ nguyên cả hai và chỉ đổi thân thành lời gọi `meets_confidence`. "Một vị từ dưới ngưỡng" của ADR-030 Ràng buộc 4 vẫn đúng: phép so nằm đúng một chỗ ở `policy.py`, và grant (ADR-030 QĐ 3) vẫn chỉ gọi `is_below_confidence`.
- Không chuyển về U1: thiết kế U1 đã qua `arch-review-design-w1b-r2.md`, mở lại thì tốn một vòng mà không lợi gì. U7b là người gọi thứ hai đầu tiên.
- Điều kiện:
  - Cùng commit: `meets_confidence`, thân mới của `is_below_confidence`, vế 5 của `auto_mode_allowed`, và hai test AST (`test_catalog_tools_reads_no_setting`, `test_single_threshold_compare` đã sửa theo L-4).
  - Mọi test U1 của `is_below_confidence` xanh **mà không sửa dòng nào** (STD-TEST-5). Đó là bằng chứng hợp đồng U1 giữ.
  - Nếu thân U1 đã merge khác chữ `design-addendum-1-U1.md:116` (ví dụ `<=`): U7b dừng `DESIGN_CONFLICT`, không chỉnh `meets_confidence` cho khớp.
- `ToolContext.threshold_pct`, `streak_required`: U7b, đợt 2, `registry.py`, theo thứ tự U1 → U6b → U7a → U7b (w2b mục 5). Có mặc định `None`. Runner bước (e) đặt giá trị. Cùng commit với vế 4. U8 không chạm.

**(3) A-U7a-16 (DDL lỗi sau commit ngầm → người xóa Custom Field mồ côi bằng tay). Chấp nhận như rủi ro còn lại. Chủ: U7a, đợt 2 (phát hiện); writer ở As-Built (hướng dẫn).**
- Phạm vi: chỉ site `test`. Ở `production`, `catalog.check` từ chối "Tạo Custom Field" (`TEST_SITE_ONLY`, `design-addendum-2-U7b-U8-fixes.md:178`). Sau ADR-035 QĐ 5, hành động này chỉ chạy trong job sau duyệt.
- Hệ quả được nhận: dòng Custom Field không có cột làm meta của `dt` có trường đó, nên mọi ghi lên `dt` có trường đó lỗi "unknown column" cho tới khi dòng bị xóa. Ca hiếm: `validate_fields_for_doctype` đã qua, chỉ còn lỗi DDL như khóa chờ hết hạn hay vượt cỡ dòng.
- Không thêm bước bù tự động. Xóa Custom Field từ bộ thực thi là một đường ghi mới (xóa, dưới tài khoản agent, ngoài danh mục, ngoài `RESTORABLE_ACTIONS`), nên cần ADR mới. Không đáng cho một ca chỉ ở site test (STD-DESIGN-5).
- Điều kiện:
  - Test `TC::TestCreateCustomField::test_ddl_failure_after_implicit_commit_reports_orphan` (`:66`) giữ.
  - Đề xuất kết thúc ở `Lỗi` và có comment kết quả.
  - Error Log `TITLE_CATALOG_FAILED` mang `orphan_custom_field=1`, `doctype`, `name`.
  - As-Built ghi bước tay: một người có System Manager xóa Custom Field `<dt>-<fieldname>` qua Desk trên site `test`. Agent không làm bước này. Kèm câu đối soát: số Error Log có `orphan_custom_field=1` chưa xử lý = số Custom Field của app mà `has_column` sai, và bằng 0 sau khi dọn.
  - Team-leader báo người như một hệ quả đã nhận, không chặn.

## 6. Điều kiện plan đợt 2 phải mang (danh sách cuối, thay các danh sách trước)

- **C-1 Thứ tự:**
  - Đợt 2 bắt đầu sau khi `team/FEAT-004` và CHG-001 vào `develop` (`arch-impact.md:168`; ADR-023 POST).
  - Merge vào `team/FEAT-007`: U5b ∥ U7a → U7b → U8 (AC-64).
  - Vào `develop` cùng lượt merge cuối đợt 2, có `cmd.migrate` (trường `rejection_comment_posted`, option Select, DocPerm).
- **C-2 File chung:** bảng w2b mục 5 giữ nguyên, thêm ba dòng:
  - `erp_ai/test_change_decision.py`: U7a, theo (1);
  - `erp_ai/agent/changes/test_transitions.py`: U7a, theo L-2;
  - `erp_ai/agent/test_authority.py`: U7b.
  - Đơn vị sau rebase rồi chạy `cmd.test_one` cho mọi file chung trước merge (K-5).
- **C-3 Cùng commit:**
  - (i) U7b: DocPerm `Agent`, 2 khóa `hooks.py`, 2 hàm hook, `open_assignment_condition`, test Sửa 1.4.
  - (ii) U7b: `decide_proposal`, dòng `PANEL_METHODS`, lời gọi `.js`.
  - (iii) U8: toàn bộ bảng Sửa 4.
  - (iv) U7a:
    - `reject` xếp job;
    - nhánh `Đã từ chối` (đặt theo C-4) và `_post_result`;
    - `claim_rejection_comment`, trường `rejection_comment_posted`;
    - các test FEAT-004 đổi theo (1), L-2.
  - (v) U7b: `meets_confidence`, thân `is_below_confidence`, `auto_mode_allowed`, hai trường `ToolContext`, runner bước (e), test AST.
- **C-4 (L-1):** nhánh `Đã từ chối` là bước đầu của job, trước phép kiểm lại người duyệt của ADR-023 và `_recheck` của FEAT-004. Kèm test `test_reject_job_skips_decider_recheck`.
- **C-5 (L-2):** nối vào `STATE_FIELDS_EXPECTED`, `STATE_VALUES` có cờ = 1, `prepare_new` đặt lại cờ.
- **C-6 (L-3):** `panel_summary` tự dựng `changes`, `edit_fields`. `record_summary` giữ tập khóa.
- **C-7 (L-4):** luật AST ngưỡng chỉ bắt toán tử thứ tự.
- **C-8:**
  - U7a ghim biểu thức sắp ToDo của `_open_assignment` thành chữ, có khóa phụ (ví dụ `creation desc, name desc`). Đây là một phần hợp đồng U7a (w2a mục 5).
  - U7b chép đúng chữ đó vào `open_assignment_condition`.
  - Test `test_assignment_edges_same_in_both_paths` có ca hai ToDo cùng `creation`.
- **C-9:** test U1 của `is_below_confidence` không bị sửa trong commit U7b. Thân U1 khác thiết kế → `DESIGN_CONFLICT`.
- **C-10:** sửa test của FEAT-004 đúng phạm vi (1): có danh sách grep dán vào báo cáo task, chỉ assertion số job, đổi tên, một dòng journal FEAT-007.
- **C-11:** A-U7a-16 theo (3). Writer ghi bước tay và câu đối soát vào As-Built.
- **C-12:** dòng test chép từ hai file sửa và file này, không từ addendum (`design-addendum-2-U7a.md:381`, `:378`; `design-addendum-2-U7b-U8.md:366`, `:370`, `:379`). Không dòng test nào kèm điều kiện.
- **C-13:** rút lui U7b theo thứ tự "gỡ DocPerm `Agent` (đối chiếu `COUNT(*) = 0`) → gỡ mã hook". As-Built chép lại.
- **C-14:** N-1 (`do_tin_cay_pct` trong `PROMPT_REQUIRED_MARKERS["classify"]`) thuộc U1 đợt 1. U1 đã merge mà thiếu thì plan chèn một task một dòng trước U7b.
- **C-15 Câu mở, không chặn (team-leader giữ):**
  - (8) "Custom Field luôn cần duyệt";
  - A-U7a-3 (trả lời "không tự gán rồi tự duyệt" → vế `assigned_by ≠ user` vào **cả** `is_assigned` và `open_assignment_condition` trong một commit);
  - A-U7b-7;
  - nhánh A/B của w2a (6);
  - duyệt ADR-035.

## 7. ADR có bị phá bởi các sửa không

| ADR | U7a-fixes-2 | U7b-U8-fixes |
|---|---|---|
| ADR-005 | Không. `_post_comment` dùng `write_ticket.post_comment` với `ticket` từ `ctx` | Không |
| ADR-010 | Không | Không. QĐ 5 và Ràng buộc import đã sửa bởi ADR-035 QĐ 4, đúng chữ (`:266-270`) |
| ADR-012 | Không. Trường mới thuộc phần trạng thái, ngoài `DIGEST_FIELDS`. Đích không đổi khi Từ chối | Không chạm |
| ADR-023 | **L-1**: thứ tự nhánh Từ chối so với phép kiểm lại ở đầu `_run` | Không chạm |
| ADR-030 | Không chạm | Nội dung đúng (một phép so ở `policy`). Cách thi hành sai: **L-4** |
| ADR-031 | Không. QĐ 3 (cùng bộ dựng), Ràng buộc 5 (cờ, không phải bộ đếm), Ràng buộc 6 (chỉ `transitions.py` ghi) đúng | Không. QĐ 4 đã sửa bởi ADR-035 QĐ 5; tool chỉ đọc `ctx` |
| ADR-032 | Không | Không. Ràng buộc 2 (`decide_proposal` không enqueue) giữ (`:308`) |
| ADR-033 | Không. QĐ 1 (ghi dưới agent, trong job), QĐ 6 (chạy lại → 0) đúng | Không. QĐ 5 đúng sau vế tự commit |
| ADR-034 | Hai file sửa không nhắc và không đổi vùng của nó | Như bên trái |
| ADR-035 | QĐ 6 đúng. Cần thêm một câu (dưới) | QĐ 1–5 đúng. L-3 là lệch hợp đồng giữa hai đơn vị, không phá QĐ 4 |

**Câu thêm vào ADR-035 QĐ 6** (architect viết ở lời gọi kế, khi ADR-035 còn `proposed`; không phải ADR mới, vì không đổi quyết định đã duyệt nào):
- "Job đăng comment sau Từ chối không ghi đích nên không chạy phép kiểm lại người duyệt của ADR-023; nhánh này đứng trước mọi kiểm của job."
- Ràng buộc thêm: test L-1.

## 8. Tự phản biện

Đã dựng các cặp task cùng tuân mọi ADR, w2b và hai file sửa mà vẫn xung đột, rồi siết:
1. CHG-001 đặt kiểm lại người duyệt ở đầu `_run`, còn U7a đặt nhánh Từ chối trong `_locked_run` sau nó. Agent được giao từ chối, job đẩy đề xuất sang `Lỗi`. Đã siết: L-1, C-4.
2. U7a sắp ToDo theo `modified desc`, U7b viết SQL theo `creation desc`. Danh sách và form lệch nhau. Đã siết: C-8.
3. U7b đọc `changes` từ `record_summary`, còn U7a ghim tập khóa. Đã siết: L-3, C-6.
4. U7a thêm trường trạng thái, test FEAT-004 ghim `STATE_FIELDS` đỏ, dev dừng. Đã siết: L-2, C-5.
5. Test AST của U7b đỏ trên chính vế 4, dev loại file ra khỏi luật. Đã siết: L-4, C-7.
6. U1 viết `is_below_confidence` khác thiết kế, U7b sửa `meets_confidence` cho khớp, hành vi U1 đổi lặng lẽ. Đã siết: C-9.
7. U7a sửa test Từ chối trên `develop` hôm nay (tên `:79`), rồi FEAT-004 merge mang tên `:239` với assertion cũ. Đã siết: (1) điều kiện trước và danh sách theo hành vi, C-1, C-10.

Sau khi siết, không còn cặp nào trong phạm vi U7a, U7b, U8 AC-64.

## Việc tiếp

- **Team-leader:**
  - ghi journal "review vòng 2 đợt 2b: approve có điều kiện";
  - gọi architect thêm câu L-1 vào ADR-035 QĐ 6 trước khi chuyển ADR-035 cho người;
  - giữ các câu ở C-15.
- **Tech-lead:** plan đợt 2 mang C-1..C-15. Chép L-1..L-4 vào task của U7a, U7b như yêu cầu bắt buộc.
- **Designer:** không còn vòng sửa nào cho hai file này.
