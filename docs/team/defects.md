# Defects

| ID | Ngày | Mô tả | Nguồn | Trạng thái |
|---|---|---|---|---|
| BUG-001 | 2026-11-12 | 400 `Your credit balance is too low…` bị xếp `bad_request` thay vì `quota`/`Hết hạn mức` (`erp_ai/gateway/breaker.py:57`, trái guide `:797`) | hội thoại, tái hiện trên `miyano` | đã sửa (team/BUG-001) |
| BUG-002 | 2026-11-12 | Test FEAT-001 (test_tasks.TestCheckPrivilegeEscalation, erp_ai_accuracy TestAccuracyTenLogSample) phụ thuộc dữ liệu sống của site: 19 test đỏ khi site có role/log/khóa thật | acceptance FEAT-002, tái hiện trên miyano | đã sửa (team/BUG-002) |
