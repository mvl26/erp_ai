# Ghi chú từ phiên FEAT-004/005 (`6c38287b`) cho phiên FEAT-007

Ngày: 2026-11-14 17:25, bổ sung 18:35 và 20:00. Người viết: team-leader của phiên đang hoàn thiện FEAT-004/005. File này chỉ để báo tin; phiên này không sửa file nào khác của FEAT-007.

## Việc cần làm ngay (người đã chọn lúc 20:00)

Người đã chọn "Phiên FEAT-007 dùng chung khóa". Từ giờ, mọi lệnh `bench --site miyano run-tests` và `bench --site miyano migrate` của phiên FEAT-007 (team-leader, tech-lead, dev, reviewer, qa) chạy qua cùng một khóa file:

```
flock -w 1800 /home/miyano/frappe-bench/apps/erp_ai/.team/miyano-site.lock <lệnh>
```

- Test cần trường mới của nhánh mình: migrate và test trong MỘT lần giữ khóa, vì migrate của nhánh khác gỡ trường của mình:
  `flock -w 1800 <khóa> sh -c 'cd /home/miyano/frappe-bench && PYTHONPATH=<worktree> bench --site miyano migrate && PYTHONPATH=<worktree> bench --site miyano run-tests --module <module>'`
- Không chạy hai lệnh test cùng lúc, kể cả trong cùng một phiên.
- Lệnh chờ khóa có thể đứng yên tới 20 phút khi phiên kia chạy cả app; đó không phải treo.

## Việc đã xảy ra trên site `miyano`

- Trong chặng cuối của build FEAT-004 (task T34, khoảng 16:10–17:22), tech-lead chạy `bench migrate` ba lần (lên / xuống / lên) bằng code của `team/FEAT-004`.
- Hệ quả tech-lead báo: 4 trường của FEAT-007 trong ERP AI Setting (`site_environment`, `act_now_enabled`, `one_click_approval_enabled`, `record_tools_enabled`) bị gỡ khỏi danh sách trường. Giá trị đã lưu còn nguyên. Phiên FEAT-007 cần chạy lại migrate từ worktree của mình.
- Lần chạy cả app của T34 có 6 `QueryDeadlockError` trùng lúc FEAT-007 migrate và test; chạy lại riêng từng test thì qua.

## Việc đang chạy từ phiên này

- FEAT-004 (`team/FEAT-004`, worktree `.claude/worktrees/feat-004`): 68/68 task; qa xác nhận 46/46 tiêu chí đạt nhưng trả `rework` vì hai test phụ thuộc thứ tự chạy (đang sửa) và chưa có lần chạy cả app nào sạch. Sau khi sửa xong sẽ có MỘT lần chạy cả app dưới khóa (15–20 phút).
- FEAT-005 (`team/FEAT-005`, worktree `.claude/worktrees/feat-005`): 5/16 task. Nhánh này thêm trường `privilege_alert_checked_until` vào ERP AI Setting và migrate từ worktree của nó. Mỗi lần như vậy gỡ 4 trường của FEAT-007 khỏi danh sách trường; ngược lại, migrate của FEAT-007 gỡ trường của FEAT-005.
- Khi FEAT-004 được nghiệm thu: merge `team/FEAT-004` vào `develop`. Đây là việc mà T56–T58 của FEAT-007 đang chờ.

## Số đo: chạy test song song trên một site tự gây deadlock

- 17:30–18:20, khi 3 qa, dev của FEAT-005 và phiên FEAT-007 cùng chạy test: cả app `Ran 1482 tests in 1149.538s`, `FAILED (failures=5, errors=18)`; `test_apply_job` `Ran 117 tests`, `FAILED (errors=56)`, cả 56 là deadlock 1213, không có assert nào sai.
- 18:55–19:15, khi các agent của phiên này đã chạy lần lượt qua khóa nhưng vẫn có test ngoài khóa: cả app `Ran 1496 tests in 1079.598s`, `FAILED (failures=1, errors=128)`, 128 lỗi là deadlock 1213.
- Cùng lúc đó, chạy riêng dưới khóa: `test_apply_job` `Ran 117 tests in 178.351s` `OK`.
- Tech-lead FEAT-005 thấy deadlock ngay cả khi đang giữ khóa, và trường `privilege_alert_checked_until` bị gỡ hai lần: có lệnh migrate và test chạy ngoài khóa.

## Điều cả hai phiên cùng gặp

- `test_runner_routing`, `test_agent_runner` (các ca `test_l1_*`) và `test_route_ticket` đỏ khi site đang lưu `auto_assign_enabled=1`. Phiên này tạm đặt `auto_assign_enabled=0` và `code_change_apps` rỗng trong lúc chạy rồi trả lại (cách người đã duyệt ngày 2026-11-13). Commit `e98a818` của FEAT-007 (ghim `auto_assign_enabled` về 0 trong lớp test nền) sửa đúng gốc của việc này.
- File cả hai bên cùng sửa, sẽ xung đột lúc hòa nhập: `erp_ai/agent/runner.py`, `erp_ai/agent/tools/site_api.py`, `erp_ai_setting.json`, `erp_ai/tasks.py`, `erp_ai/tests/test_architecture.py`, `erp_ai/tests/test_doctype_descriptions.py`.
- Ở cây chính có `erp_ai/test_change_decision.py` bị sửa lúc 10:45 và chưa commit; không phải của phiên này, phiên này để nguyên.
