# FEAT-007 R-5: lịch chạy (`scheduler_events`), giờ site, chạy bù, hàng đợi `long`

Ngày: 2026-11-14 · Người làm: researcher · Tiêu chí: AC-16, AC-51, AC-55, AC-59 · Chưa chốt gì thay architect: chỉ khuyến nghị.

## Phiên bản đang dùng
- frappe 15.126.1 (`apps/frappe/frappe/__init__.py:54`), croniter ~=6.0.0 (`apps/frappe/pyproject.toml:43`, cài: `env/lib/python3.*/site-packages/croniter-6.0.0.dist-info`), rq 1.15.1 (`env/lib/python3.*/site-packages/rq-1.15.1.dist-info`).
- bench CLI: `/usr/local/lib/python3.12/dist-packages/bench` (mẫu supervisor đọc ở đây).
- Mọi `path:line` dưới đây là trong `apps/frappe/frappe/` trừ khi ghi khác.

## Tóm tắt
| Câu | Trả lời một câu | Độ tin cậy |
|---|---|---|
| (a) cú pháp | Khóa `cron` của `scheduler_events` nhận chuỗi croniter 5 trường; giờ tính theo múi giờ của System Settings của site (không phải giờ máy chủ) | cao (mã); giá trị múi giờ của site production: UNVERIFIED |
| (b) bỏ lỡ | Không chạy bù từng lần: lần quét lịch kế tiếp thấy "đến hạn" và chạy ĐÚNG MỘT lần, các lần lỡ gộp lại | cao |
| (c) hàng đợi | Job `cron` chạy ở hàng `default`, timeout 300 s; hàng `long` (1500 s) chỉ có ở các khóa `*_long`/`*_maintenance`, mà các khóa này cố định 00:00 | cao |
| (d) worker `long` | Production dựng bằng supervisor có chương trình `...-frappe-long-worker`; kiểm bằng `supervisorctl status` và danh sách worker trong Redis (lệnh ở mục d) | cao (mẫu); tình trạng thật trên server: UNVERIFIED |

## (a) Khai báo lịch và múi giờ

### Cơ chế
- `scheduler_events` trong hooks: giá trị dạng danh sách → tần suất cố định; giá trị dạng dict → khóa `cron`, mỗi khóa con là chuỗi cron, giá trị là danh sách hàm. `scheduled_job_type.py:214-232` (`insert_events`, `insert_cron_jobs`). Mỗi hàm thành một bản ghi `Scheduled Job Type`, tần suất "Cron" kèm `cron_format` (`scheduled_job_type.py:244-279`).
- Chuỗi cron phải qua `croniter(...)`, sai thì lỗi (`scheduled_job_type.py:60-69`). Chính hooks của frappe dùng khóa `cron` với `"0/15 * * * *"` và `"0 6 * * *"` (`hooks.py:218-243`).
- Bản ghi chỉ được tạo/cập nhật khi chạy `sync_jobs()`: gọi trong `bench migrate` (`migrate.py:142`) và lúc cài app (`installer.py:333`). Sửa `hooks.py` mà không `bench migrate` thì lịch không đổi (docs.frappe.io cũng nói vậy).
- Bản ghi tìm theo `method` (`scheduled_job_type.py:253`) và tên bản ghi là 2 đoạn cuối của đường dẫn hàm (`scheduled_job_type.py:52-53`): một hàm chỉ đứng ở MỘT lịch; hai hàm trùng 2 đoạn cuối (ví dụ `tasks.run` của hai module) sẽ đụng tên. Đặt tên hàm lịch riêng, không trùng.
- Khóa cố định của Frappe (đã đọc `CRON_MAP`, `scheduled_job_type.py:112-126`): `daily` = `0 0 * * *` (00:00); `weekly` = `0 0 * * 0` = 00:00 Chủ nhật (không phải thứ Hai); `monthly` = `0 0 1 * *`; `hourly` = `0 * * * *`. Vì vậy 08:00 và thứ Hai bắt buộc phải dùng khóa `cron`.

### Các khai báo cần có (đã kiểm bằng croniter 6.0.0, mốc giả định thứ Bảy 2026-11-14 09:07)
| Nhu cầu | Chuỗi cron | Ba lần chạy kế tiếp tính ra |
|---|---|---|
| Mỗi 15 phút (AC-16) | `*/15 * * * *` (frappe dùng cách viết `0/15 * * * *`, cùng nghĩa) | 09:15, 09:30, 09:45 |
| Hằng ngày 08:00 (AC-51) | `0 8 * * *` | 2026-11-15 08:00, 11-16 08:00, 11-17 08:00 |
| Thứ Hai 08:00 (AC-55) | `0 8 * * 1` | 2026-11-16 08:00 (thứ Hai), 11-23, 11-30 |
| Mỗi tháng (AC-59): ngày 1 lúc 08:00 | `0 8 1 * *` | 2026-12-01 08:00, 2027-01-01, 2027-02-01 |

Mục sẽ ghi trong `erp_ai/hooks.py` (tên hàm mới là CHỖ GIỮ CHỖ; designer đặt tên thật; hai khóa hiện có giữ nguyên, xem `erp_ai/hooks.py:159-162`):
```python
scheduler_events = {
	"hourly": ["erp_ai.tasks.reprobe_exhausted_keys"],
	"daily": ["erp_ai.tasks.recompute_monthly_spend", "erp_ai.tasks.check_privilege_escalation"],
	"cron": {
		"*/15 * * * *": ["erp_ai.tasks.<ten_ham_quet_bu>"],
		"0 8 * * *": ["erp_ai.tasks.<ten_ham_bao_cao_coo>"],
		"0 8 * * 1": ["erp_ai.tasks.<ten_ham_kpi_tuan>"],
		"0 8 1 * *": ["erp_ai.tasks.<ten_ham_ra_soat_thang>"],
	},
}
```
Nếu muốn mốc tháng là 00:00 ngày 1 thì dùng khóa `"monthly"` có sẵn (tương đương `0 0 1 * *`); spec AC-59 không nêu giờ nên đây là lựa chọn của designer.

### Múi giờ
- `is_event_due` so `get_next_execution()` với `now_datetime()` (`scheduled_job_type.py:89-92`); `get_next_execution` tính croniter trên `last_execution` (hoặc `creation`) kiểu naive (`scheduled_job_type.py:135-140`).
- `now_datetime()` = giờ UTC đổi sang "múi giờ hệ thống" rồi bỏ tzinfo (`utils/data.py:313-315`), múi giờ hệ thống = `System Settings.time_zone` của site, trống thì `Asia/Kolkata` (`utils/data.py:327-329`). `last_execution` cũng ghi bằng `now_datetime()` (`scheduled_job_type.py:166,179`).
- Kết luận: "08:00" = 08:00 theo `System Settings.time_zone` của site; múi giờ của máy chủ và TZ của tiến trình không tham gia. Đúng với NFR-5 "08:00 giờ của site". Bẫy: nếu trường trống thì thành 08:00 giờ Ấn Độ. Tài liệu docs.frappe.io không nói gì về múi giờ (đã đọc); kết luận lấy từ mã.
- Nhịp quét của scheduler mặc định 60 s (`utils/scheduler.py:247-248`, khóa `scheduler_tick_interval`): job có thể trễ tới ~1 phút so với mốc.
- UNVERIFIED (chỉ kiểm được trên server production): `System Settings.time_zone` của site production. Lệnh cho người chạy: `cd <bench> && bench --site <site> execute frappe.utils.get_system_timezone` (kỳ vọng `Asia/Ho_Chi_Minh`).

## (b) Lần chạy bị lỡ khi scheduler hoặc worker ngừng
- Scheduler chỉ lưu `last_execution` trên bản ghi. Mỗi tick, `enqueue_events` duyệt các job `stopped=0` (`utils/scheduler.py:114-129`); `enqueue` chạy khi `get_next_execution() <= now` (`scheduled_job_type.py:71-92`), và `get_next_execution` là lần khớp cron ĐẦU TIÊN sau `last_execution`. Ngừng qua nhiều mốc → khi bật lại, mốc đầu đã quá hạn → đẩy MỘT job; các mốc lỡ tiếp theo không đẩy thêm. Không có hàng bù, không có "misfire grace".
- `last_execution` được ghi lúc job BẮT ĐẦU (`scheduled_job_type.py:178-179`), không phải lúc xong. Mốc kế tiếp tính từ giờ bắt đầu thực tế. Hệ quả: scheduler hồi phục lúc 09:00 thì báo cáo 08:00 chạy lúc 09:00 một lần; sau đó mốc kế là 08:00 hôm sau. Job chết giữa chừng hoặc quá timeout không được thử lại cho đến mốc kế tiếp (`execute` bắt lỗi, ghi "Failed", không retry: `scheduled_job_type.py:142-156`).
- Job chưa có `last_execution` (mới tạo bởi `bench migrate`) dùng `creation` làm mốc (`scheduled_job_type.py:131-135`): job `0 8 * * *` tạo lúc 09:00 chạy lần đầu vào 08:00 hôm sau, không chạy ngay.
- Chỉ scheduler ngừng: không có gì được đẩy. Chỉ worker ngừng: job đã đẩy nằm trong Redis chờ (RQ không đặt TTL cho job xếp hàng; `utils/background_jobs.py:139-149`); trong lúc đó `is_job_in_queue` (`scheduled_job_type.py:74,94-100`, mã `scheduled_job::<method>`) chặn đẩy trùng nên không dồn nhiều bản. Việc Redis mất hàng đợi khi khởi động lại: UNVERIFIED (phụ thuộc cấu hình bền vững của Redis queue trên production; lệnh: `redis-cli -p <cổng redis_queue trong common_site_config.json> CONFIG GET appendonly` và `CONFIG GET save`).
- Scheduler không chạy khi: `maintenance_mode`, `pause_scheduler`, `disable_scheduler` hoặc `System Settings.enable_scheduler` tắt (`utils/scheduler.py:132-161`); trong maintenance mode job còn bị chặn ở `run_scheduled_job` (`scheduled_job_type.py:197-200`). Chỉ một tiến trình scheduler mỗi bench (khóa file `config/scheduler_process`: `utils/scheduler.py:43-50`).
- Hệ quả thiết kế cho spec (để designer/architect cân nhắc, không phải quyết định): (1) AC-16 quét bù mỗi 15 phút tự chịu được lỡ nhịp vì mỗi lần quét tính lại từ dữ liệu, không từ số lần lỡ; (2) AC-55 KPI tuần chạy muộn vào thứ Ba vẫn phải tính "tuần trước" theo lịch chứ không theo giờ chạy, và nếu ngừng hơn một tuần thì chỉ MỘT lần chạy xảy ra, tuần giữa sẽ không có dòng trừ khi hàm tự quét các tuần thiếu; (3) AC-59 làm tương tự theo tháng; (4) cả hai cần chống trùng riêng (NFR-3) vì job có thể chạy lại khi `Run Now` thủ công (`execute_event`, `scheduled_job_type.py:189-194`).

## (c) Hàng đợi và timeout của job lịch
- `ScheduledJobType.enqueue` gọi `enqueue(..., queue=self.get_queue_name(), job_type=..., job_id=...)` KHÔNG truyền timeout (`scheduled_job_type.py:75-80`). `get_queue_name` trả `long` chỉ khi tần suất chứa "Long" hoặc "Maintenance", ngược lại `default` (`scheduled_job_type.py:182-183`). Tần suất của job `cron` là "Cron" → hàng `default`.
- Không truyền timeout → `get_queues_timeout()[queue]` (`utils/background_jobs.py:134-135`): `default` 300 s, `short` 300 s, `long` 1500 s (`utils/background_jobs.py:42-56`; cache `docs/team/research/frappe-enqueue@15.126.1.md` khớp). Mọi hàng trong `workers` của `common_site_config.json` có thể ghi đè timeout theo tên hàng (cùng dòng 42-56): chưa kiểm trên production, UNVERIFIED; không khuyến nghị đổi cấu hình bench cho tính năng này.
- Các khóa `hourly_long`, `daily_long`, `weekly_long`, `monthly_long` ánh xạ sang tần suất "... Long" (`scheduled_job_type.py:235-241`: `event_type.replace("_"," ").title()`) và chạy ở `long`, nhưng giờ cố định 00:00 (Chủ nhật cho weekly, ngày 1 cho monthly). Không có tổ hợp "08:00 + hàng long" trong `scheduler_events`.

### Phương án cho job 08:00 cần quá 300 s (khuyến nghị cho architect, chưa quyết)
| Phương án | Giờ | Hàng/timeout | Rủi ro | Chi phí |
|---|---|---|---|---|
| A: hàm đứng thẳng trong khóa `cron` | 08:00 | default / 300 s | Quá 300 s thì bị RQ giết, không thử lại tới mốc sau | thấp nhất |
| B: hàm trong khóa `cron` chỉ xếp một job thứ hai `frappe.enqueue(..., queue="long", timeout=<giây>, job_id=<cố định>, deduplicate=True)` | 08:00 | long / tùy chọn (tối đa nên < `stopwaitsecs` 1560 s của supervisor `long`) | cần worker `long` đang chạy (mục d); thêm một bước | thấp |
| C: khóa `daily_long` / `weekly_long` / `monthly_long` | 00:00 (không phải 08:00) | long / 1500 s | không đạt AC-51/AC-55 đúng giờ | thấp |
Khuyến nghị: A cho quét 15 phút (AC-16, việc ngắn, mỗi phiếu xếp job riêng) và cho job còn thấy chạy dưới vài chục giây; B cho báo cáo 08:00, KPI tuần, rà soát tháng nếu khối lượng dữ liệu có thể vượt 300 s. Lý do: giữ đúng mốc 08:00 giờ site, và job nặng không chặn hàng `default` (nơi email, quét phiếu đang chạy). Cờ `deduplicate` cần `job_id` (`utils/background_jobs.py:99-103`). `frappe.enqueue` chạy với người dùng của phiên tại lúc xếp (cache enqueue).

## (d) Kiểm worker hàng `long` trên production
- Mẫu bench: `setup supervisor` tạo ba chương trình `<bench>-frappe-default-worker` (`worker --queue default`), `<bench>-frappe-short-worker`, `<bench>-frappe-long-worker` (`worker --queue long`, và `,default,short` khi frappe > 14.18, tức bench này) cộng `<bench>-frappe-schedule`; số tiến trình mỗi loại = `background_workers` (`/usr/local/lib/python3.12/dist-packages/bench/config/templates/supervisor.conf:30-72,137-143`; `bench/config/supervisor.py:106-118`). Bench dev này chỉ có `Procfile` `worker: bench worker` không chỉ định hàng, nên một worker ăn mọi hàng gồm `long` (`utils/background_jobs.py:287-327` với `queue=None` → `get_queue_list` trả mọi hàng, `425-436`); `sites/common_site_config.json` có `background_workers: 1`.
- Tên hàng trong Redis có tiền tố mã bench: `<bench_id>:long` (`utils/background_jobs.py:542-549`).
- Lệnh người cần chạy trên server production (UNVERIFIED cho tới khi chạy; chỉ đọc):
  1. `sudo supervisorctl status | grep -E "worker|schedule"` → phải có dòng `...-frappe-long-worker-0 RUNNING`; nếu bench dùng systemd/docker thì thay bằng `systemctl list-units | grep -i worker` hoặc `docker compose ps` (cấu trúc triển khai của production: chưa biết).
  2. `cd <bench> && bench --site <site> doctor` → in "Workers online: N" (tổng, không theo hàng; `utils/doctor.py:96-98,131-134`) và nêu scheduler bị tắt/tạm dừng/bảo trì.
  3. Theo hàng: `cd <bench> && bench --site <site> execute frappe.utils.background_jobs.get_workers` rồi, nếu cần tên hàng, trong `bench --site <site> console` chạy `[(w.name, w.queue_names()) for w in frappe.utils.background_jobs.get_workers()]` → phải có ít nhất một worker có `<bench_id>:long` trong danh sách hàng. (`Worker.queue_names` có ở `rq/worker.py:333`.)
  4. Trạng thái scheduler của site: `bench --site <site> scheduler status` → "enabled"; và `Scheduled Job Log` của job có `status` mới (cho thấy job thật chạy).
- Cảnh báo: số `Workers online` > 0 không chứng minh có worker `long` (có thể toàn worker `default`/`short`); phải đọc danh sách hàng như bước 3 hoặc cấu hình supervisor. Nếu thiếu worker `long`, phương án B ở mục (c) sẽ đứng chờ vô hạn; kiểm tra AC nên có ca "job xếp hàng long mà không worker → báo".

## Sources
- https://docs.frappe.io/framework/user/en/basics/hooks (mục Scheduler Events; truy cập 2026-11-14): khóa `cron` nhận chuỗi croniter hợp lệ, `*_long` chạy ở worker long, cần `bench migrate` sau khi sửa lịch, không nói gì về múi giờ.
- https://docs.frappe.io/framework/user/en/api/background_jobs (qua cache `docs/team/research/frappe-enqueue@15.126.1.md`, truy cập 2026-11-11): `enqueue`, `job_id`, `deduplicate`, timeout mặc định các hàng.
- Mã nguồn cài trên bench (frappe 15.126.1, đọc 2026-11-14): `apps/frappe/frappe/core/doctype/scheduled_job_type/scheduled_job_type.py`, `apps/frappe/frappe/utils/scheduler.py`, `apps/frappe/frappe/utils/background_jobs.py`, `apps/frappe/frappe/utils/data.py`, `apps/frappe/frappe/utils/doctor.py`, `apps/frappe/frappe/hooks.py`, `apps/frappe/frappe/migrate.py`, `apps/frappe/frappe/installer.py`, `apps/frappe/frappe/core/doctype/scheduled_job_type/test_scheduled_job_type.py` (test weekly: kỳ vọng Chủ nhật).
- Mẫu supervisor của bench: `/usr/local/lib/python3.12/dist-packages/bench/config/templates/supervisor.conf`, `/usr/local/lib/python3.12/dist-packages/bench/config/supervisor.py`.
- Kiểm tính chuỗi cron: croniter 6.0.0 cài trong `env`, chạy tính thuần (không chạm site `miyano`).
- Đã có từ trước, không làm lại: `docs/team/features/FEAT-007/audit-A8.md` dòng A8-1 ("daily" = 00:00, app chưa có khóa `cron`).
