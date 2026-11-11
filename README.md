### ERP AI agent

Agent AI hỗ trợ công việc trên ERP Miyano. Giai đoạn 1: Helpdesk. Agent đọc phiếu mới (và comment có từ khóa), phân loại vào 1 trong 6 đầu mục A–F, và ở mức `L1` ghi hướng giải quyết, comment trên phiếu. App cài xong ở trạng thái **tắt**.

Phạm vi hiện tại: mức `L0` và `L1`. Mức `L2`/`L3` chọn được trên form nhưng chỉ cấp đúng bộ tool của `L1`.

| Mức | Agent làm gì |
|---|---|
| `L0` (shadow) | Chỉ chạy bước phân loại, ghi dự đoán vào `ERP AI Log`, không đổi phiếu. Comment có từ khóa được ghi nhật ký "bỏ qua do L0", không gọi API |
| `L1` | Ghi loại phiếu, nhóm, ưu tiên, độ tin cậy, hướng giải quyết, comment; tạo Task khi có người có role `ERP AI Instructor` ra lệnh. Không đổi `status`, không ghi đè phân loại do người đã đặt |

Khi vượt ngân sách tháng, mức hiệu lực lui về `L1` (không bao giờ nâng `L0` lên `L1`).

### Yêu cầu

- Frappe `>=15.126.1,<16.0.0`, Helpdesk 15.1.0 trở lên (comment phiếu là core `Comment`; bản Helpdesk cũ hơn sẽ không kích hoạt được bằng comment).
- Thư viện `anthropic>=0.103.1,<1` (khai trong `pyproject.toml`).
- Khóa API Anthropic loại workspace chuẩn (`sk-ant-api03-`), nhập trên form cấu hình.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench --site <site> install-app erp_ai
bench --site <site> migrate
```

Cài và migrate (chạy lại được, không ghi đè cấu hình đã lưu) tạo: role `ERP AI Agent` và `ERP AI Instructor`; tài khoản `ai.agent@miyano.com.vn` chỉ có role `ERP AI Agent` và `Agent` (không có System Manager); các trường AI trên HD Ticket (permlevel 8, ẩn với khách); `ERP AI Setting` ở trạng thái tắt, mức `L0`.

### Cấu hình và bật

Mở `/app/erp-ai-setting` (chỉ System Manager):

1. Thêm khóa API ở bảng khóa; bấm "Kiểm tra khóa" để thử từng khóa.
2. Đặt `monthly_budget_usd` (mặc định 10), bốn đơn giá token (mặc định 0; phải > 0 mới bật được) và model (không có giá trị nào viết cứng trong mã).
3. Rà các giá trị mặc định: `excluded_teams` (mặc định "Nhân sự & Hành chính" và "Tài chính Kế toán", mỗi nhóm một dòng: phiếu các nhóm này và phiếu có cờ "không dùng AI" không bao giờ được gửi lên API), `trigger_keyword` (mặc định `@ai`), `category_mapping` (đầu mục A–F sang loại phiếu/nhóm/ưu tiên), `alert_recipients` (mặc định `info@miyano.com.vn`).
4. Giữ `L0` đủ lâu để đo độ chính xác (báo cáo `ERP AI Accuracy`), rồi mới tích `enabled` và chuyển `L1`.

Cấp role `ERP AI Instructor` cho người được phép ra lệnh agent trên mọi phiếu; người được giao phiếu chỉ có thẩm quyền trên đúng phiếu đó.

Chi tiết các việc phải làm trước khi bật: `docs/team/features/FEAT-001/asbuilt.md`, mục 6.

### Bộ đánh giá offline

Đo độ chính xác phân loại trên phiếu đã gán nhãn người, trước khi bật agent. Phiếu nhóm loại trừ không được xuất.

```bash
bench --site <site> execute erp_ai.eval.export_tickets.export --args '["<đường dẫn .jsonl ngoài repo>"]'
bench --site <site> execute erp_ai.eval.run_eval.run --args '["<đường dẫn .jsonl>"]'
```

`export` từ chối đường dẫn nằm trong repo. `run` gửi nội dung lên API bằng cùng prompt với agent thật và in: độ chính xác tổng, theo từng đầu mục, ma trận nhầm lẫn 6×6, độ chính xác trên phiếu không do người viết nhiều nhất tạo, và kết luận (≥ 85% / 70–85% / < 70%).

### Running tests

```bash
cd $PATH_TO_YOUR_BENCH
bench --site <site> run-tests --app erp_ai
```

Site phải bật `allow_tests`. Test không gọi mạng thật (lời gọi model được thay bằng stub). Không đặt file test tên `test_runner.py`: Frappe bỏ qua tên này (test kiến trúc kiểm điều đó).

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/erp_ai
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
