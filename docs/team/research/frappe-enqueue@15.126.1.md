# frappe.enqueue @ 15.126.1 — chống trùng, after_commit, user của job (cache)

Ngày: 2026-11-11 · Phiên bản: frappe 15.126.1, rq 1.15.1 · Nguồn gốc: FEAT-001 research Q2-H-3 · Mã: `frappe/utils/background_jobs.py`.

- Có `job_id`, `deduplicate`, `enqueue_after_commit`, `timeout`. `deduplicate` thiếu `job_id` → throw.
- Kiểm trùng chạy lúc gọi `enqueue` (bỏ qua nếu QUEUED/STARTED; job cũ đã xong thì xóa). Việc đẩy job chạy sau commit qua `frappe.db.after_commit` (không lọc trùng), RQ `rpush` không kiểm trùng → gọi hai lần trong cùng giao dịch thì cùng id bị đẩy hai lần. Cần tự chặn trùng trong request.
- Timeout mặc định: short/default 300 s, long 1500 s → truyền `timeout` tường minh.
- Job chạy với `frappe.session.user` tại lúc enqueue (`execute_job` gọi `set_user`) → muốn chạy dưới tài khoản khác thì phải đổi user trong job.
- `after_commit` chỉ chạy khi `frappe.db.commit()` → test không commit thì không thấy job trong Redis; đếm callback hoặc thay `enqueue` bằng stub.

## Sources
- https://docs.frappe.io/framework/user/en/api/background_jobs (truy cập 2026-11-11)
