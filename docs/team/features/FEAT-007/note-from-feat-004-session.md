# Ghi chú từ phiên FEAT-004/005 (`6c38287b`) cho phiên FEAT-007

Ngày: 2026-11-14 17:25, bổ sung 18:35, 20:00, 2026-11-15 00:05 và 02:50. Người viết: team-leader của phiên hoàn thiện FEAT-004/005, nay làm CHG-002. File này chỉ để báo tin; phiên này không sửa file nào khác của FEAT-007.

## Cập nhật 2026-11-15 02:50: việc mới CHG-002 đụng file chung

Người ra lệnh lúc 00:55: "làm nốt đi, mục tiêu cuối bot có thể sửa được tất cả, core code lẫn trên data", rồi chọn "Giữ vành đai an toàn". Phiên này mở **CHG-002** (change-request trên FEAT-004): một đề xuất gồm nhiều file và lệnh, tạo thư mục, xóa và đổi tên file, nới giới hạn kích thước, bot tự restart sau khi người bấm Duyệt. Hồ sơ: `docs/team/features/CHG-002/{intake,spec,arch-impact,design}.md`, ADR-040.

- **Phần dữ liệu không thuộc CHG-002.** Công cụ bản ghi, 5 công tắc, danh mục trắng, đề xuất ghi bản ghi vẫn là của FEAT-007. CHG-002 không sửa `site_api.py`, `registry.py`, `policy.py`, `runner.py`, `erp_ai_setting.json`.
- **Số ADR:** phiên này dùng ADR-040. Xin đừng dùng lại số 040.
- **File cả hai bên cùng sửa** (bảng đầy đủ, kèm cách giải từng xung đột, ở `docs/team/features/CHG-002/design.md` mục 1.6):
  - trong phạm vi CHG-002 mà FEAT-007 đã sửa: `erp_ai/agent/tools/source.py` (`resolve_safe_path`), `erp_ai/constants.py`, `tools/test_source.py`, `tools/test_change_guard.py`;
  - ngoài phạm vi nhưng CHG-002 buộc phải sửa: `erp_ai/agent/prompts.py` (thân `CHANGE_TOOLS_BLOCK`), `erp_ai/tests/test_architecture.py`, `erp_ai/test_utils.py`, `erp_ai/agent/test_classification.py`, `tools/test_registry.py`, `agent/test_agent_runner.py`;
  - task chưa build của FEAT-007 sẽ đụng: T89, T105 (`propose_change.py`), T72..T107 (`prompts.py`).
- **Thứ tự gộp đề xuất:** CHG-002 vào `develop` trước; sau đó FEAT-007 gộp `develop` vào `team/FEAT-007` một lần ở task T56. Nếu phiên FEAT-007 muốn thứ tự khác thì ghi vào file này hoặc báo người.
- CHG-002 thêm DocType con `ERP AI Change Operation`. Migrate bằng code không có DocType này sẽ xóa bản ghi DocType đó như "Orphaned", giống hai DocType của FEAT-007 bên dưới.
- CHG-002 build ở worktree riêng và chạy test qua khóa `miyano-site.lock` như trước.

## Cập nhật 2026-11-15 00:05: FEAT-004 và FEAT-005 đã vào `develop`

- FEAT-004 đã merge vào `develop` (`4469287`). FEAT-005 (17/17 task, qa `accepted`) đã merge vào `develop` (`464063f`). Việc T56–T58 của FEAT-007 đang chờ FEAT-004 thì nay làm được.
- Các lần migrate của phiên này trong hai lần giữ khóa 23:28–23:37 và 23:43–23:53 ngày 14/11 đã:
  - xóa bản ghi DocType `ERP AI User Template` và `ERP AI Catalog Rule` của FEAT-007, vì Frappe coi là "Orphaned" khi migrate bằng code không có hai DocType này;
  - gỡ các trường của FEAT-007 khỏi ERP AI Setting, như các lần trước.
  Phiên FEAT-007 cần migrate lại từ worktree của mình trước khi test, trong cùng một lần giữ khóa với lệnh test.
- Bản ghi Report `ERP AI Accuracy`: JSON của nhánh FEAT-007 thêm role `ERP AI Instructor` (`modified` 2026-11-14 12:00:02). Test `test_report_record_is_system_manager_only_script_report` trên `develop` đòi chỉ có `System Manager`. Phiên này hai lần tạm đưa bản ghi về JSON của nhánh FEAT-005 để chạy cả app, rồi trả lại bản của FEAT-007 (đọc lại khớp role và `modified`). Khi FEAT-007 hòa `develop` vào, JSON và test này phải được sửa cho khớp nhau trong nhánh FEAT-007.
- Kết quả cả app của nhánh FEAT-005 (gồm toàn bộ code FEAT-004), mỗi lần trong một lần giữ khóa: `Ran 1564 tests in 503.462s` `OK` (tech-lead) và `Ran 1564 tests in 488.122s` `OK` (qa), 0 deadlock.

## Quy ước khóa (người đã chọn lúc 20:00 ngày 14/11)

Người đã chọn "Phiên FEAT-007 dùng chung khóa". Mọi lệnh `bench --site miyano run-tests` và `bench --site miyano migrate` của phiên FEAT-007 (team-leader, tech-lead, dev, reviewer, qa) chạy qua cùng một khóa file:

```sh
flock -w 1800 /home/miyano/frappe-bench/apps/erp_ai/.team/miyano-site.lock <lệnh>
```

- Test cần trường mới của nhánh mình: migrate và test trong MỘT lần giữ khóa, vì migrate của nhánh khác gỡ trường của mình:
  `flock -w 1800 <khóa> sh -c 'cd /home/miyano/frappe-bench && PYTHONPATH=<worktree> bench --site miyano migrate && PYTHONPATH=<worktree> bench --site miyano run-tests --module <module>'`
- Không chạy hai lệnh test cùng lúc, kể cả trong cùng một phiên.
- Lệnh chờ khóa có thể đứng yên tới 20 phút khi phiên kia chạy cả app; đó không phải treo.
- Lúc 23:27 ngày 14/11 phiên này thấy phiên FEAT-007 đang giữ khóa (migrate và bốn module test); hai lần chạy cả app của phiên này sau đó không gặp deadlock nào.

## Việc đã xảy ra trên site `miyano` trước đó

- Trong chặng cuối của build FEAT-004 (task T34, khoảng 16:10–17:22 ngày 14/11), tech-lead chạy `bench migrate` ba lần (lên / xuống / lên) bằng code của `team/FEAT-004`.
- Hệ quả tech-lead báo: 4 trường của FEAT-007 trong ERP AI Setting (`site_environment`, `act_now_enabled`, `one_click_approval_enabled`, `record_tools_enabled`) bị gỡ khỏi danh sách trường. Giá trị đã lưu còn nguyên. Phiên FEAT-007 cần chạy lại migrate từ worktree của mình.
- Nhánh FEAT-005 thêm trường `privilege_alert_checked_until` vào ERP AI Setting; migrate của FEAT-007 gỡ trường này, và ngược lại.

## Số đo: chạy test song song trên một site tự gây deadlock

- 17:30–18:20 ngày 14/11, khi 3 qa, dev của FEAT-005 và phiên FEAT-007 cùng chạy test: cả app `Ran 1482 tests in 1149.538s`, `FAILED (failures=5, errors=18)`; `test_apply_job` `Ran 117 tests`, `FAILED (errors=56)`, cả 56 là deadlock 1213, không có assert nào sai.
- 18:55–19:15, khi các agent của phiên này đã chạy lần lượt qua khóa nhưng vẫn có test ngoài khóa: cả app `Ran 1496 tests in 1079.598s`, `FAILED (failures=1, errors=128)`, 128 lỗi là deadlock 1213.
- Cùng lúc đó, chạy riêng dưới khóa: `test_apply_job` `Ran 117 tests in 178.351s` `OK`.
- 23:28–23:53, khi lúc bắt đầu mỗi lần giữ khóa không có lệnh `run-tests`/`migrate` nào ngoài khóa: hai lần cả app `OK` nêu ở trên.

## Điều cả hai phiên cùng gặp

- `test_runner_routing`, `test_agent_runner` (các ca `test_l1_*`) và `test_route_ticket` đỏ khi site đang lưu `auto_assign_enabled=1`. Phiên này tạm đặt `auto_assign_enabled=0` và `code_change_apps` rỗng trong lúc chạy rồi trả lại (cách người đã duyệt ngày 2026-11-13). Commit `e98a818` của FEAT-007 (ghim `auto_assign_enabled` về 0 trong lớp test nền) sửa đúng gốc của việc này.
- File cả hai bên cùng sửa từ FEAT-004/005, sẽ xung đột lúc hòa nhập: `erp_ai/agent/runner.py`, `erp_ai/agent/tools/site_api.py`, `erp_ai_setting.json`, `erp_ai/tasks.py`, `erp_ai/tests/test_architecture.py`, `erp_ai/tests/test_doctype_descriptions.py`.
