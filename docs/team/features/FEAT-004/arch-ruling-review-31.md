Feature: FEAT-004
Stage: architect
Author-agent: architect
Date: 2026-11-14

# Phán quyết: mục `("eval/export_tickets.py", "_inside_repo")` trong `ROOT_CHECK_ALLOWLIST` (T31) so với ADR-011

## Câu hỏi
review-31 (mục "Không kiểm được từ diff"): mục cho phép hợp ý định ADR-011 QĐ 4 nhưng trái chữ Ràng buộc `ADR-011.md:44` ("không có hàm khử symlink/kiểm gốc thứ hai trong `erp_ai/**`"). Thu hẹp, ghi ngoại lệ, hay chuyển sang helper chung ở `source.py`?

## Bằng chứng (đọc trong worktree feat-004, 2026-11-14)
- Phạm vi của quyết định: `ADR-011.md:29-30` QĐ 4 chỉ nói về **bộ chặn đường dẫn ghi và lệnh `bench` của tool đề xuất và job áp dụng**; dòng 44 là phép kiểm của QĐ đó, `erp_ai/**` là phạm vi grep để bắt bản sao của bộ chặn ấy. Một Ràng buộc không rộng hơn Quyết định nó kiểm.
- `erp_ai/eval/export_tickets.py:13-17`: kiểm **ngược** (từ chối khi nằm TRONG repo `erp_ai`, cho mọi chỗ khác); có từ FEAT-001 (`07cea99`, 2026-11-11, trước ADR-011), hợp đồng ở `FEAT-001/design.md:412`; người gọi là người qua `bench execute`, không phải model.
- `resolve_safe_path` (`erp_ai/agent/tools/source.py:108-120`) giam trong `apps/` + mẫu tên cấm + đuôi cho phép: ngữ nghĩa ngược, không dùng thay được. Thêm helper "ngoài repo" vào `source.py` = đưa việc của eval vào module tool đọc nguồn (STD-STRUCT-5) và buộc `eval` phụ thuộc `agent/tools` chỉ cho một lời gọi.
- Không tới được từ agent: `LAYER_RULES` cấm `erp_ai.agent` import `erp_ai.eval` (`erp_ai/tests/test_architecture.py:70-80`).
- Danh sách cho phép đã đóng đúng 2 mục, có ca "cùng hàm khác file"/"cùng file khác hàm" bị bắt (`test_architecture.py:4226-4250`); lý do ghi ngay tại mục (`:1883-1884`).

## Phán quyết
**Chấp nhận với điều kiện; T31 không đổi.** Mục này không phải "bộ chặn thứ hai" theo nghĩa QĐ 4, vì nó không nằm trên đường ghi nào của tool hay job áp dụng. Điều kiện (đều đã có test, phải giữ nguyên):
1. `ROOT_CHECK_ALLOWLIST` đóng, đúng 2 mục (`test_root_check_allowlist_is_closed`); thêm mục thứ ba cần phán quyết architect mới.
2. Luật tầng `erp_ai.agent` không import `erp_ai.eval` (`test_architecture.py:70-80`) giữ nguyên; nới luật này thì mục cho phép mất hiệu lực.
3. `_inside_repo` chỉ được gọi trong `export_tickets.py`; dùng nó ở module khác là vi phạm (đã bắt bởi ca "cùng hàm khác file").

Không chọn: chuyển sang helper ở `source.py` (ngữ nghĩa ngược, sai chiều phụ thuộc); ghi ngoại lệ bằng cách sửa thân ADR lúc này (lệnh giao cấm sửa ADR).

## Việc kèm (không chặn T31)
- architect, lần sửa ADR-011 tới (hoặc trước khi `accepted`): dòng 44 thêm "…trong `erp_ai/**`, trừ các mục `ROOT_CHECK_ALLOWLIST` không nằm trên đường ghi của tool hoặc job áp dụng (arch-ruling-review-31)".
- Mục deferred `_build_app_reason` (`erp_ai/agent/tools/change_guard.py:202-214`): nằm trong chính module bộ chặn duy nhất của QĐ 4 (kiểm tên app cho bộ chặn lệnh), không phải bộ chặn thứ hai → hợp ADR-011. Mở rộng `ROOT_CHECK_CALLS` (`relative_to`, `commonprefix`, `startswith`) là việc chất lượng test, tech-lead quyết; ADR không đòi.
