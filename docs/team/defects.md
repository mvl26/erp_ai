# Defects

| ID | Ngày | Mô tả | Nguồn | Trạng thái |
|---|---|---|---|---|
| BUG-001 | 2026-11-12 | 400 `Your credit balance is too low…` bị xếp `bad_request` thay vì `quota`/`Hết hạn mức` (`erp_ai/gateway/breaker.py:57`, trái guide `:797`) | hội thoại, tái hiện trên `miyano` | mở |
