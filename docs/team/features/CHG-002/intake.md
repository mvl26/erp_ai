Feature: CHG-002
Stage: intake
Author-agent: team-leader
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake CHG-002 — Bot sửa được tất cả: mở rộng đường sửa code lõi

- Yêu cầu gốc: "làm nốt đi, mục tiêu cuối bot có thể sửa được tất cả, core code lẫn trên data"
- Nguồn: hội thoại (2026-11-15)
- Loại việc: change
- Playbook: change-request
- Size: L
- Mode: decide
- Feature gốc: FEAT-004 (đường sửa code và chạy lệnh bench; đã `verified`, nằm trong `develop`)
- Lý do chọn playbook/cỡ: yêu cầu đổi các giới hạn đã có trong spec và ADR của FEAT-004: mỗi đề xuất chỉ một file, không xóa hay đổi tên file (`erp_ai/agent/tools/propose_change.py:225-297`, ADR-011 QĐ 1 và 4, ADR-013 QĐ 6), không tạo thư mục mới và giới hạn kích thước (`propose_change.py:169-197`), danh sách 6 lệnh bench không có restart (`erp_ai/agent/tools/change_guard.py:33-36`, ADR-022 QĐ 2), sau khi sửa file .py người phải tự restart (`erp_ai/agent/change_text.py:113`). Chạm ba ADR về an toàn và nhiều module (`tools/change_guard.py`, `tools/propose_change.py`, `agent/changes/**`, `constants.py`, `process_runner.py`) nên cỡ L.
- Skill tạm: không cần
- Ngân sách: max_agents_per_feature = 10; feature_budget_usd = không giới hạn

## Hiện trạng đã rà (Explore, 2026-11-15, mã `develop` @ `cf69b57`)

Bot làm được hôm nay:

- Code: đề xuất sửa một file có sẵn, tạo một file mới, hoặc chạy một trong 6 lệnh bench; người có role `ERP AI Instructor` bấm Duyệt thì job áp dụng ghi file và commit cục bộ; hoàn tác được. Áp cho mọi app nằm trong `code_change_apps`, gồm cả `frappe`, `erpnext`, `helpdesk`, `hrms` (`change_guard.py:138-183`).
- Dữ liệu: tạo, sửa bản ghi của mọi DocType không bị cấm; khi bật "Toàn quyền" thì thêm xóa, submit, hủy và gọi hàm (`erp_ai/agent/tools/site_api.py:306-389`, `registry.py:66-78`). Ghi ngay, không qua bước duyệt, không có hoàn tác.

Còn thiếu so với "sửa được tất cả":

| # | Điểm | Chỗ trong mã | Loại |
|---|---|---|---|
| 1 | Sửa file .py xong không có hiệu lực cho tới khi người restart | `change_text.py:113`; `change_guard.py:33-36` | chưa làm |
| 2 | Mỗi đề xuất một file; không gộp "sửa code + migrate" thành một lần duyệt | `propose_change.py:225-297` | cấm có chủ ý (ADR-011 QĐ 1) |
| 3 | Không tạo được thư mục mới (không dựng được module hay DocType mới bằng code) | `propose_change.py:196-197` | chưa làm |
| 4 | Không xóa, không đổi tên file | không có tool | cấm có chủ ý (ADR-011 QĐ 4, ADR-013 QĐ 6) |
| 5 | File mới ≤ 20 000 ký tự; ≤ 10 chỗ sửa mỗi đề xuất; file ≤ 1 MiB | `propose_change.py:169-197`, `constants.py:47-48` | giới hạn kỹ thuật |
| 6 | Chỉ 8 loại đuôi file (.py .js .vue .json .md .html .css .txt) | `tools/source.py:27` | giới hạn kỹ thuật |
| 7 | Lệnh bench ngoài 6 lệnh (restart, execute, console, install-app…) | `change_guard.py:33-40`, `:261-283` | cấm có chủ ý (ADR-022 QĐ 2) |
| 8 | Sửa chính app `erp_ai` | `change_guard.py:159-160`; `policy.py:115-116` | cấm có chủ ý (ADR-011 QĐ 4) |
| 9 | File khóa, mật khẩu, cấu hình site, `.git`, push | `source.py:28-31`; `process_runner.py:104-125` | cấm có chủ ý (ADR-011 QĐ 4, ADR-022 QĐ 2) |
| 10 | Bot tự duyệt đề xuất của mình | `erp_ai_change_proposal.py:101-106` | cấm có chủ ý (ADR-012 QĐ 4–5, ADR-023 QĐ 1–2) |

## Quyết định của người (AskUserQuestion, 2026-11-15)

| # | Câu hỏi | Người chọn | Hệ quả cho spec |
|---|---|---|---|
| N-1 | Mở tới đâu: có cho bot sửa chính `erp_ai` và chạy lệnh bench bất kỳ không | "Giữ vành đai an toàn" | Mở các điểm 1–6 của bảng cho `frappe`, `erpnext`, `helpdesk`, `hrms` (và app khác trong `code_change_apps`): nhiều file trong một lần duyệt, tạo thư mục và DocType mới, xóa và đổi tên file, bỏ giới hạn kích thước, bot tự restart sau khi người bấm Duyệt. Điểm 7: danh sách lệnh bench chỉ thêm restart; execute, console và lệnh khác vẫn cấm. Điểm 8, 9, 10 giữ nguyên: không sửa app `erp_ai`, không đụng file khóa/mật khẩu/cấu hình site, không `.git`/push, bot không tự duyệt. Mỗi đề xuất vẫn cần người bấm Duyệt. |

## Quyết định của team-leader (decide mode)

| # | Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|---|
| QĐ-1 | CHG-002 chỉ làm đường sửa code; phần dữ liệu (công cụ bản ghi, 5 công tắc, danh mục trắng, đề xuất ghi bản ghi có duyệt và hoàn tác) để FEAT-007 | Phiên khác đang build FEAT-007 (36/62) và các task chưa làm của nó sửa `policy.py`, `registry.py`, `runner.py`; người đã chọn N-1 của FEAT-007 hôm 14/11: 5 quyền ngày 13/11 giữ dưới dạng công tắc riêng (`docs/team/features/FEAT-007/intake.md:38`) | Mở cả phần dữ liệu ở đây | `analyze --amend` thêm tiêu chí sau khi FEAT-007 merge |
| QĐ-2 | Build song song với FEAT-007 ở worktree riêng, cắt từ `develop` | Người đã chọn "Build toàn bộ song song" cho FEAT-007 (N-3); theo `git diff --stat` ngày 2026-11-15 nhánh `team/FEAT-007` chưa sửa file nào của đường sửa code | Chờ FEAT-007 merge xong | Dừng build, rebase sau |

## Ranh giới với FEAT-007 (phiên khác đang build)

- CHG-002 chỉ đụng: `erp_ai/agent/tools/change_guard.py`, `tools/propose_change.py`, `tools/source.py`, `agent/changes/**`, `agent/constants.py`, `agent/change_text.py`, DocType `ERP AI Change Proposal` và test của chúng.
- CHG-002 không sửa: `erp_ai/agent/tools/site_api.py`, `agent/registry.py`, `agent/policy.py`, `agent/runner.py`, `erp_ai_setting.json` (nếu thiết kế buộc phải thêm trường cài đặt thì nêu rõ để báo phiên FEAT-007).
- Hai phiên dùng chung site `miyano`: mọi `run-tests` và `migrate` chạy qua khóa `.team/miyano-site.lock`.

## Điểm analyst phải chốt (decide, ghi rõ giả định)

- Tiêu chí cho từng điểm 1–7 theo N-1, và tiêu chí chứng minh vành đai (điểm 8, 9, 10) còn nguyên sau khi mở.
- "Một lần duyệt cho nhiều thay đổi": một đề xuất gồm nhiều file và các lệnh đi kèm (migrate, build, restart) được duyệt và hoàn tác như một khối.
- Restart do bot chạy sau khi được duyệt: hôm nay tài khoản hệ điều hành `miyano` không có quyền (`sudo` đòi mật khẩu; bench chạy dưới supervisor). Cách làm do architect và designer chọn; phần người phải làm một lần trên máy thì ghi rõ.

## Ràng buộc lúc nhận việc

- Push lên GitHub vẫn bị từ chối (403), nên chưa có PR và CI; chuỗi dừng ở merge cục bộ vào `develop`.
- Code mới chỉ có hiệu lực trên site sau khi người chạy `bench --site miyano migrate` và `bench restart` (cần mật khẩu `sudo`).

## Đổi cỡ (nếu có)

