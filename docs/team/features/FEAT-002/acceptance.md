Feature: FEAT-002
Stage: verify
Author-agent: qa
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Acceptance FEAT-002

Commit kiểm: `7ea066a5de6584a6849f27c784b8b35172c15985` (nhánh `team/FEAT-002`, checkout chính, không đổi nhánh).

Nguồn bằng chứng:
- Lần QA trước chạy các lệnh lúc 14:59–15:05 ngày 2026-11-12. Log nằm trong scratchpad `/tmp/claude-1000/-home-miyano-frappe-bench-apps-erp-ai/cc03198d-c63c-4da7-8d33-b479609b0cf2/scratchpad/`.
- Các log này hợp lệ cho commit trên. Commit cuối có đổi mã là `b8f6a3f` (14:45:30). `git diff --name-only b8f6a3f HEAD -- erp_ai | wc -l` → `0`. `7ea066a` (14:50:59) chỉ thêm tài liệu.
- Team-leader yêu cầu không chạy lại các lệnh đã có bằng chứng. Lần QA này chỉ chạy truy vấn đọc DB (a)–(c), grep diff, và đọc log/junit.

## Tiêu chí
Lệnh test của từng module: `cmd.test_one` với `{file}` = tệp test. Log: `mod_<module>.log` và `.xml`.

| criterion | command | exit / output excerpt | covering test | verdict |
|---|---|---|---|---|
| AC-1 | `cmd.test_one` `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`; `cmd.test_one` `erp_ai/tests/test_install.py` | `Ran 19 tests in 0.879s` `OK`; `Ran 22 tests in 9.477s` `OK` | `S::test_status_fields_defaults`, `S::test_status_fields_rejections` (biên −1/31, min > max, 5001 ký tự), `S::test_status_fields_valid_edges_save`, `I::test_status_defaults_filled_only_when_missing`, `I::test_emptied_thinking_text_survives_setup` | đạt |
| AC-2 | `cmd.test_one` `erp_ai/agent/test_runner_status.py` | `Ran 39 tests in 10.151s` `OK` | `R::test_start_signal_before_first_model_call`, `R::test_ticket_insert_l0_gets_start_signal`, `R::test_feature_adds_no_comment_task_or_ticket_change` | đạt |
| AC-3 | `cmd.test_one` `erp_ai/agent/test_answer_delay.py`; như AC-2 | `Ran 8 tests in 0.005s` `OK`; `Ran 39 … OK` | `D::test_delay_always_within_min_max`, `D::test_wait_capped_by_run_deadline` (biên hạn chót), `D::test_out_of_range_db_values_are_clamped`, `R::test_answer_waits_from_start_signal`, `R::test_indicator_stays_thinking_while_waiting` | đạt |
| AC-4 (gồm R-2 rollback) | như AC-2 | `Ran 39 … OK` | `R::test_done_last_*` (8 nhánh, gồm `…on_unexpected_runner_exception`), `R::test_done_reaches_page_on_rollback_branch` | đạt |
| AC-5 | như AC-2 | `Ran 39 … OK` | `R::test_skipped_runs_emit_nothing_and_never_wait` (4 nhánh bỏ qua), `R::test_empty_text_no_signal_delay_still_applies` (`""`, `"   "`), `R::test_ticket_insert_never_waits` | đạt |
| AC-6 (c), (e) | như AC-2 | `Ran 39 … OK` | `R::test_mention_run_counts_once_for_daily_limit`, `R::test_model_messages_same_with_feature_on_and_off` | đạt |
| AC-7 | như AC-2; `cmd.test_one` `erp_ai/agent/test_run_status.py` | `Ran 39 … OK`; `Ran 9 tests in 0.021s` `OK` | `R::test_start_signal_failure_still_answers_and_logs_class`, `R::test_working_signal_failure_…`, `R::test_done_signal_failure_logged_to_error_log_class_only`, `R::test_status_text_never_in_logs`, `E::test_emit_never_raises_and_records_class` | đạt |
| AC-8 | `cmd.test` (`full_app.log` 14:59); `cmd.test_one` `erp_ai/agent/test_agent_runner.py`, `erp_ai/tests/test_handlers.py` | `Ran 591 tests in 106.464s` `FAILED (failures=16, errors=3)`; `Ran 56 … OK`; `Ran 31 … OK` | `R::test_same_gateway_calls_and_cost_with_feature_on_and_off` | **đạt về ý, chữ không đạt.** Ý của AC-8 là "không đổi hành vi cũ", và ý này đạt: 19 test đỏ đều nằm trong 2 module FEAT-002 không sửa; cùng site data thì danh sách đỏ trên code FEAT-001 giống hệt (xem "Kiểm chung"). Chữ "toàn bộ test hiện có của app xanh" thì không đạt. Ghi là BUG-002, không phải hồi quy của FEAT-002 |
| AC-9 | như AC-2 và AC-7 | `Ran 39 … OK`; `Ran 9 … OK` | `R::test_signal_sequence_read_tool_then_answer`, `R::test_ticket_insert_l1_signal_sequence`, `E::test_every_granted_tool_and_classify_step_has_label`, `E::test_unknown_tool_gets_fallback_label`, `R::test_tool_arguments_and_ticket_text_never_in_payload` | đạt |
| AC-10 (a)–(i) | bước tay của người (spec: phần sau bàn giao; `ui: false`, không có Playwright) | test tĩnh hỗ trợ: `cmd.test_one` `erp_ai/tests/test_architecture.py` → `Ran 58 tests in 0.484s` `OK` (`A::test_status_script_static_rules`) | bước tay ở mục "Bước tay cho người" | **chờ người**. Theo DoD của spec, việc này thuộc phần sau G4/bàn giao |
| AC-11 | bước tay của người (J1, A-21) | test tĩnh `A::test_status_script_static_rules` (đọc `expires_in_s`, có `setTimeout`, không viết cứng `600`): `OK` | bước tay ở mục "Bước tay cho người" | **chờ người**, cùng lý do như AC-10 |
| AC-12 | `cmd.test_one` `erp_ai/tests/test_install.py`; `cmd.migrate` lên → lên → gỡ → lên; truy vấn đọc (c) | `Ran 22 … OK`; xem "Migration"; DB lúc kiểm: đúng 1 bản ghi `ERP AI Agent Status`, `dt=HD Ticket`, `enabled=1`, `apply_to=Form`, `apply_to_customer_portal=0`, `is_standard=0`; `script equals repo file: True file len 4803` | `I::test_status_script_installed_once_matching_repo_file`, `I::test_status_script_reset_when_changed_on_site`, `I::test_status_script_served_to_agent_page_only`, `I::test_unchanged_status_script_is_not_saved_again`, `I::test_uninstall_removes_only_status_script`, `I::test_uninstall_without_record_is_noop` | đạt |

Ngoài đường chính (bước 4): các nhánh biên và lỗi trong test plan đều nằm trong các module xanh ở trên: biên −1/31/5001 (AC-1), hạn chót và giá trị DB ngoài khoảng (AC-3), rollback (AC-4), bỏ qua và chuỗi rỗng (AC-5), phát tín hiệu hỏng ở 3 bước (AC-7). Đã kiểm 28 tên test lấy từ test plan: tên nào cũng có đúng 1 lần trong junit của module tương ứng.

Chất lượng test (bước 7): giá trị kỳ vọng viết cứng. Ví dụ `Đang suy nghĩ…`/3/5, `sleep(3)`, các chuỗi lỗi ở mục 3.1. Review-04 bắt được lỗ hổng "chuyển chờ sát khối `post_comment` vẫn xanh" (STD-TEST-2) và đã thêm test cho D-6. Các vòng T10 thêm self-test để chứng minh từng bộ quét kiến trúc bắt được vi phạm giả. Không thấy test nào không thể đỏ.

### NFR
| NFR | Bằng chứng | verdict |
|---|---|---|
| NFR-1, NFR-2 | `D::test_delay_always_within_min_max`, `D::test_fixed_delay_when_min_equals_max`, `D::test_wait_capped_by_run_deadline`, `S::test_status_fields_rejections` (cận 30): `OK` | đạt |
| NFR-3 | `R::test_same_gateway_calls_and_cost_with_feature_on_and_off`: `OK` | đạt |
| NFR-4' | `E::test_payload_has_exactly_seven_keys`, `R::test_tool_arguments_and_ticket_text_never_in_payload`, `R::test_status_text_never_in_logs`: `OK` | đạt |
| NFR-5 | `R::test_done_after_last_log_entry`: `OK`. Phần trên trình duyệt kiểm ở bước tay AC-10 (b), (c) | đạt phía server; phía trang chờ người |
| NFR-6 | `R::test_feature_adds_no_comment_task_or_ticket_change`, `A::test_run_status_writes_nothing`: `OK` | đạt |

## Kiểm chung
- `cmd.test` (`cd ../.. && bench --site miyano run-tests --app erp_ai`, `full_app.log`/`.xml`, 14:59): `Ran 591 tests in 106.464s` → `FAILED (failures=16, errors=3)`.
  - Theo junit, 19 test đỏ đều thuộc 2 module FEAT-002 không sửa:
    - `erp_ai.tests.test_tasks.TestCheckPrivilegeEscalation`: 15 test (12 failure, 3 error);
    - `erp_ai.erp_ai_agent.report.erp_ai_accuracy.test_erp_ai_accuracy.TestAccuracyTenLogSample`: 4 test.
  - So với nền, cùng site data:
    - test_tasks: `cur_erp_ai.tests.test_tasks.log` → `Ran 33 tests in 1.003s` `FAILED (failures=12, errors=3)`; `f001_erp_ai.tests.test_tasks.log` (code team/FEAT-001) → `Ran 33 tests in 0.847s` `FAILED (failures=12, errors=3)`.
    - accuracy: `cur_…test_erp_ai_accuracy.log` → `Ran 13 tests in 0.397s` `FAILED (failures=4)`; `f001_…` → `Ran 13 tests in 0.521s` `FAILED (failures=4)`.
    - Team-leader đã so: hai bên có cùng 19 tên test.
  - `git diff --name-only 23ded66 HEAD` (merge-base với team/FEAT-001) không có `test_tasks.py`, `tasks.py` hay thư mục `report/erp_ai_accuracy`.
  - Phân loại: lỗi môi trường/test có sẵn, không phải lỗi của FEAT-002. Chi tiết ở BUG-002.
- Các module FEAT-002 chạy riêng (`cmd.test_one`), tất cả `OK`, cộng 242 test:
  - `test_agent_runner` `Ran 56`;
  - `test_answer_delay` `Ran 8`;
  - `test_runner_status` `Ran 39`;
  - `test_run_status` `Ran 9`;
  - `test_erp_ai_setting` `Ran 19`;
  - `test_architecture` `Ran 58`;
  - `test_handlers` `Ran 31`;
  - `test_install` `Ran 22`.
- `cmd.lint` (`pre-commit run --all-files`, `lint.log` 15:04): 12 dòng `Passed`, 0 dòng `Failed`. Gồm `Run ruff linter…Passed`, `Run ruff formatter…Passed`, `prettier…Passed`, `eslint…Passed`; `eslint` và `prettier` cũng kiểm tệp `.js`.
- `cmd.typecheck`: slot rỗng trong profile, không áp dụng.
- `cmd.build`: design 6.1 nói không cần, vì tệp `.js` được đọc lúc cài, không phải bundle. Không chạy.
- Dấu skip mới trong diff:
  - So với `develop` (memory: `base_branch` "main" không có, `develop` là nền đã xác nhận): grep `skip_markers` trên các dòng `+` của `*.py`/`*.js`, bỏ `test_architecture.py` vì tệp này chứa chuỗi giả dùng cho bộ quét → rỗng.
  - Chỉ phần FEAT-002, `git diff 23ded66 HEAD -- '*.py' '*.js' | grep -E "^\+.*(@unittest\.skip|skipIf|expectedFailure|\.skipTest\(|xfail)"` → rỗng.
  - Dòng `self.assert` bị xóa trong phần FEAT-002: `0`. Dòng thêm: `264`.
- `protected_paths` (`.env`, `.env.*`, `**/*.pem`, `**/*.key`, `license.txt`): diff không đụng tệp nào (grep rỗng).
- Helpdesk không bị sửa: `git -C ../helpdesk status --porcelain` → 3 dòng: `M desk/auto-imports.d.ts`, `M desk/yarn.lock`, `M yarn.lock`. mtime của 3 tệp là 2026-11-11 10:21–10:38, trước commit FEAT-002 đầu tiên (`bc4baf6`, 2026-11-12 12:58). Vậy 3 dòng này không do FEAT-002 tạo ra.
- Migration (`cmd.migrate` = `cd ../.. && bench --site miyano migrate`). Thứ tự xác định từ mtime log và dấu vết trong DB:
  1. `migrate1.log` 15:05:07: lên;
  2. `migrate2.log` 15:05:31: lên lần hai, kiểm AC-12 "chạy hai lần" và lặp không đổi;
  3. `down.log` 15:05:32: bước xuống 6.2.1 (`before_uninstall`). `tabDeleted Document` có `deleted_name='ERP AI Agent Status'`, `creation=2026-11-12 15:05:32.882997`;
  4. `migrate3.log` 15:05:56: lên lại. Bản ghi hiện tại có `creation=2026-11-12 15:05:55.938931`.
  - Mỗi log migrate có 58 dòng, kết thúc bằng `Queued rebuilding of search index for miyano`, không có `Traceback`.
  - Đối soát 6.3 sau lần lên lại:
    - đúng 1 bản ghi, script khớp tệp repo;
    - `thinking_text='Đang suy nghĩ…'`, `answer_delay_min_s='3'`, `answer_delay_max_s='5'`;
    - các giá trị cấu hình khác không bị ghi đè, xem (b).
  - "`modified` không đổi ở lần lên hai" không đọc lại được trên DB vì bản ghi đã được tạo lại sau bước gỡ. Phủ bằng `I::test_unchanged_status_script_is_not_saved_again` (`OK`).

## Truy vấn đọc trên `miyano` (lần QA này, không đổi dữ liệu, không in khóa)
**(a) `Has Role` của `ai.agent@miyano.com.vn`**
- Có 99 dòng. **Có `System Manager`.**
- Mọi dòng có `creation = 2026-11-11 13:46:15.267139`, bằng `creation` của User. Frappe chép `creation` của cha sang dòng con, nên `creation` không cho biết lúc thêm role.
- `owner`: `ERP AI Agent` và `Agent` là `Administrator` (do bước cài). 97 dòng còn lại là `tài khoản quản trị của người dùng`. `modified_by` của mọi dòng: `tài khoản quản trị của người dùng`.
- Version `spr34j6nam`, `2026-11-12 11:21:13`, owner `tài khoản quản trị của người dùng`: `added: 97`, `removed: 0`, trong đó có `System Manager`. `User.modified = 2026-11-12 11:21:12.894204`, `modified_by = tài khoản quản trị của người dùng`.
- Version cũ hơn `o7au09q55s`, `2026-11-11 13:22:41`, Administrator: chỉ thêm `ERP AI Agent`, `Agent`.
- Kết luận:
  - 97 role thừa được thêm trong **một lần lưu User**, phiên của tài khoản người `tài khoản quản trị của người dùng`, lúc 2026-11-12 11:21. Đây không phải rò rỉ từ test: test chạy với user Administrator, và Version ghi user của phiên.
  - Giả thuyết "test commit làm rò rỉ" **không được xác nhận**. Các lệnh commit trong mã đều có điều kiện `if not frappe.flags.in_test`: `erp_ai/agent/runner.py:73-74`, `erp_ai/agent/run_log.py:31-32`.
  - Test thêm role (`erp_ai/tests/test_tasks.py:267,381,429` `_add_role("System Manager")`, `erp_ai/tests/test_install.py:240`) chạy trong `addCleanup(frappe.db.rollback)` (`test_tasks.py:173-174`).

**(b) `ERP AI Setting` hiện tại** (`tabSingles`; `modified = 2026-11-12 13:54:34.793007`, `modified_by = tài khoản quản trị của người dùng`)
| Mục | Hiện tại | Người đặt sáng nay |
|---|---|---|
| enabled | `1` | 1 |
| permission_level | **`L3`** | L1 |
| excluded_teams | **`''` (rỗng)** | `Nhân sự & Hành chính\nTài chính Kế toán` |
| monthly_budget_usd | **`100`** | 10 |
| giá input / cache write / cache read / output | `0.1` / `0.125` / `0.01` / `0.5` | 0.1 / 0.125 / 0.01 / 0.5 |
| thinking_text / min / max (FEAT-002) | `Đang suy nghĩ…` / `3` / `5` | mặc định |
| credentials | 1 dòng: label `Chính`, enabled `1`, status `Hoạt động`, `error_count 0`, `last_success_at 2026-11-12 14:17:20` | — |

- `tabVersion` không có dòng nào cho `ERP AI Setting`. Doctype Single này không lưu lịch sử, nên không biết từng mục đổi lúc nào.
- `ERP AI Log` có 3 dòng `stop_reason='level_L0'`, `trigger=comment_mention`, trên phiếu thật `43067`/`43068`, lúc 13:49:34–13:51:20. Vậy lúc đó mức đang là `L0`, khớp với việc người thấy `level_L0`.
- Lần lưu cuối là phiên `tài khoản quản trị của người dùng` lúc 13:54:34, ngay sau đó. Lần lưu này để lại L3 / excluded rỗng / budget 100. Có hai khả năng không phân biệt được: người tự đổi các mục này, hoặc form mở ra đã mang sẵn giá trị lạ rồi được lưu lại.
- Ai đặt `L0` trước 13:49: **không xác định được**.
  - Các test có đặt mức: `test_handlers.py:234` `set_agent_settings(enabled=1, permission_level="L0")`; `test_install.py:247` (L2) và `:255` (NULL, rồi `ensure_setup` điền L0).
  - Có lượt chạy test ngay trước đó (`base.log` 13:36, `base2.log` 13:37), nhưng không tìm được đường commit nào trong mã app. Chỉ là giả thuyết, cần dev kiểm (BUG-002, ý 3).

**(c) `HD Form Script`**: 1 bản ghi, `ERP AI Agent Status` (`dt=HD Ticket`, `enabled=1`, `apply_to=Form`, `apply_to_customer_portal=0`, `is_standard=0`, owner Administrator, `length(script)=4803`, khớp tệp repo). Đúng như ADR-007.

## Lỗi ghi nhận cho team-leader (không sửa mã)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major (BUG-002) | STD-TEST-6 | `erp_ai/tests/test_tasks.py:172-301` (`TestCheckPrivilegeEscalation`); `erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py` (`TestAccuracyTenLogSample`) | Test phụ thuộc dữ liệu sống của site: role thật của `ai.agent@…` (97 role thừa) và các dòng `ERP AI Log` thật (`Lists differ … != []`, `11 != 10`). Trên `miyano` hiện tại 19 test đỏ, giống hệt ở code FEAT-001. Có từ FEAT-001, không phải hồi quy FEAT-002 | Trong `setUp`, cô lập dữ liệu: chụp và đặt lại role của agent; lọc log theo bản ghi do test tạo hoặc theo khoảng thời gian riêng. `/team:intake` thành bug riêng |
| critical (sự cố cấu hình, cho người) | STD-SEC-4 | site `miyano`: `tabHas Role` parent `ai.agent@miyano.com.vn` | Tài khoản agent đang có `System Manager` cùng 96 role ngoài danh sách cho phép (FEAT-001 có kiểm leo quyền), và đang chạy ở `L3`, `enabled=1`. Lần lưu User lúc 2026-11-12 11:21 của phiên `tài khoản quản trị của người dùng` đã thêm các role này | Người xác nhận lần thêm role có chủ ý không; nếu không, gỡ các role thừa và đặt lại `permission_level` / `excluded_teams` / `monthly_budget_usd` theo cấu hình sáng nay. Đội không tự sửa dữ liệu site |
| minor (ý 3 của BUG-002) | STD-TEST-6 | `erp_ai/tests/test_handlers.py:234`, `erp_ai/tests/test_install.py:247,255` | `permission_level=L0` có trên site lúc 13:49–13:51 mà không rõ nguồn; có lượt chạy test ngay trước đó. Không có Version để quy trách nhiệm | Dev kiểm có đường commit nào ngoài mã app không (ví dụ commit ngầm do DDL trong test runner); bật track changes hoặc thêm log khi đổi mức |
| minor (design, journal D-6) | STD-DESIGN-5 | `docs/team/features/FEAT-002/design.md` D-13 và mục 3.6 | D-13 nói "cảnh báo cả lúc cài và lúc gỡ"; mục 3.6 nói lúc gỡ "không có thì không làm gì". Code theo 3.6 (review-09, deferred). Hành vi chấp nhận được, không làm AC-12 sai | Designer chọn một và sửa design (`/team:design FEAT-002 --amend`), cùng lúc làm As-Built |

## Bước tay cho người (AC-10, AC-11)
Thực hiện trên `miyano`, desktop, đăng nhập bằng tài khoản HD Agent, không phải `ai.agent@…`. Cấu hình phải ở `L1+` và `enabled=1`. Ghi kết quả từng ý (đạt/không, kèm ảnh nếu có) vào cuối tệp này.
1. Chuẩn bị: mở `ERP AI Setting`, ghi lại giá trị hiện tại. Mở DevTools, tab Console.
2. (a) Mở `/helpdesk/tickets/<id>` của một phiếu thử. Thêm comment `@ai tóm tắt phiếu này`. Kỳ vọng:
   - không tải lại trang mà chỉ báo hiện ra, có tên tài khoản agent và chữ `Đang suy nghĩ…`;
   - khi agent đọc phiếu hoặc tra nguồn thì chữ đổi thành `Đang làm: <nhãn>…`, ví dụ "đọc phiếu", "viết trả lời".
3. (b) Câu trả lời của agent hiện ra. Kỳ vọng: chỉ báo mất trong ≤ 10 s.
4. (c) Tạm tắt khóa API: bỏ tick `enabled` của credential `Chính`. Gõ `@ai …`. Kỳ vọng: chỉ báo không đứng quá 10 s. Bật lại credential.
5. (d) Mở phiếu đó trên cổng khách bằng tài khoản khách, trong lúc một lần chạy đang diễn ra. Kỳ vọng: không thấy chỉ báo.
6. (e) Đổi `thinking_text` thành `Đang xử lý thử…`, lưu, gõ `@ai …`. Kỳ vọng: chỉ báo hiện đúng chuỗi đó. Trả lại `Đang suy nghĩ…`.
7. (f) Đổi `thinking_text` thành `<b>x</b>`. Kỳ vọng: chỉ báo hiện đúng các ký tự `<b>x</b>`, không in đậm. Trả lại giá trị cũ.
8. (g) Không có lần chạy nào: duyệt danh sách phiếu và vài phiếu khác. Kỳ vọng: Console không có lỗi mới từ script `ERP AI Agent Status`.
9. (h) Mở hai phiên (hai trình duyệt hoặc hai tài khoản) trên cùng phiếu. Phiên B thêm một comment thường. Kỳ vọng: phiên A thấy ngay, không tải lại trang. Làm hai lần: lúc không có lần chạy và lúc đang chạy `@ai`.
10. (i) Gõ `@ai …` trên phiếu A, chuyển sang phiếu B trong cùng tab, rồi quay về A trong lúc lần chạy còn diễn ra. Kỳ vọng: ở B không có chỉ báo; ở A chỉ có một chỉ báo.
11. AC-11:
    - gõ `@ai …`; khi chỉ báo hiện, dừng worker (`bench` worker hàng `long`/`default`; ví dụ dừng supervisor worker hoặc kill tiến trình worker);
    - giữ trang mở. Kỳ vọng: chỉ báo tự mất chậm nhất 600 s sau lúc hiện;
    - tải lại trang. Kỳ vọng: chỉ báo không hiện lại;
    - bật lại worker.
12. Trả cấu hình về đúng giá trị đã ghi ở bước 1 (Constraints: không để lại thay đổi cấu hình).

## Acceptance checklist (6)
1. Mỗi tiêu chí có lệnh, đầu ra, kết luận: đạt (AC-10/AC-11 là bước tay của người theo DoD spec, chưa làm).
2. `cmd.test`/`cmd.lint`/`cmd.typecheck` xanh: **trượt về chữ** (STD-TEST-3). `cmd.test` đỏ 16F/3E. Danh sách đỏ giống hệt nền FEAT-001 và nằm trong module FEAT-002 không sửa (BUG-002). `cmd.lint` xanh; `cmd.typecheck` không có slot.
3. Không có dấu skip mới: đạt (STD-TEST-4).
4. Migration lên → lên → xuống → lên, đối soát khớp: đạt (STD-OPS-2, STD-OPS-3).
5. Phần build của DoD:
   - đạt: AC-1..AC-9 và AC-12 có test tự động; có test rollback R-2; không còn mã comment tạm (diff FEAT-002 không có); `.js` nằm trong `erp_ai/public/js/`; lint sạch; Helpdesk không bị FEAT-002 sửa; `cmd.migrate` chạy được; commit local, không push;
   - ngoại lệ: dòng "`cmd.test` xanh", như mục 2.
6. Không đụng `protected_paths`, không có secret: đạt (STD-SEC-1).

## DoD
- [x] Phần build, ngoại lệ "`cmd.test` xanh" (lỗi có sẵn, BUG-002)
- [ ] As-Built: `/team:asbuilt` sau G4. Owner: team-leader → tech-writer. Có dòng "chạy lại bước tay AC-10 sau mỗi lần nâng cấp Helpdesk/Frappe"
- [ ] README/tài liệu người dùng (chỉ báo, nhãn việc, cách tắt, khoảng trễ, cảnh báo ghi đè A-22): `/team:asbuilt`
- [ ] CHANGELOG: `/team:asbuilt`
- [ ] Bước tay AC-10 (a)–(i), AC-11: người, sau bàn giao

## Lý do chọn verdict
Team-leader đặt quy tắc: nếu mọi AC của FEAT-002 đạt và phần đỏ duy nhất là lỗi có sẵn, giống hệt nền, thì verdict là `accepted` kèm ghi lỗi.

Điều kiện đó đúng ở đây:
- AC-1..AC-9 và AC-12 đạt bằng test tự động.
- AC-8 đạt về ý: không có hồi quy.
- 19 test đỏ giống hệt trên code FEAT-001 với cùng dữ liệu, nằm trong module FEAT-002 không đụng tới, và nguyên nhân là dữ liệu site (role do người thêm, log thật).

Hai chỗ lệch với tiêu chuẩn QA chặt, ghi rõ để team-leader/người có thể bác:
- checklist mục 2 không đạt về chữ;
- AC-10 và AC-11 chưa có kết quả. Spec xếp hai mục này vào phần sau bàn giao, nên không coi là `NOT VERIFIABLE` của bước build.

Trước khi phát hành, người cần xử lý sự cố quyền của tài khoản agent (bảng lỗi, dòng critical).

Verdict: accepted
