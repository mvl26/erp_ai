# anthropic Python SDK @ 0.103.1 — kết luận (cache)

Ngày: 2026-11-11 · Phiên bản: anthropic 0.103.1 (bench env `env/lib/python3.12/site-packages/anthropic-0.103.1.dist-info`), httpx 0.28.1 · Nguồn gốc: FEAT-001 research Q1.

- Đọc header: `client.messages.with_raw_response.create(...)` → `.headers` (httpx.Headers), `.parse()` → `Message`.
- Header hạn mức: `anthropic-ratelimit-{requests,tokens,input-tokens,output-tokens}-{limit,remaining,reset}`, reset theo RFC 3339, `tokens-remaining` làm tròn tới nghìn; `retry-after` tính bằng giây, không có ở 429 do trần chi tiêu. Chưa kiểm trên response thật với API version `2023-06-01` (`UNVERIFIED`).
- Mặc định: `max_retries=2` (retry 408/409/429/≥500/lỗi kết nối, kể cả timeout), timeout 600 s, connect 5 s. Cầu dao do app tự quản → `max_retries=0`.
- Ánh xạ lỗi: 400 BadRequest, 401 Authentication, 403 PermissionDenied, 404, 409, 413, 422, 429 RateLimit, 529 Overloaded, ≥500 InternalServer; **402 → `APIStatusError` (không có lớp riêng)**.
- Hết tiền / hạn mức: 402 `billing_error`; 429 `error.details.error_code = enforced_spend_limit_reached`; 400 "You have reached your specified (workspace) API usage limits".
- Usage: `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `cache_creation`; tổng input = cả ba loại input cộng lại; ghi cache 1,25× (5 phút) / 2× (1 giờ), đọc cache 0,1× (có ngoại lệ theo model).
- Env dùng chung: `workflowcore` khai `anthropic>=0.39.0` và truyền `temperature` (đã bị gỡ ở 1.x) → không nâng lên ≥1 nếu chưa sửa `workflowcore`.
- Docs hiện hành viết cho SDK 2.x (httpx2, API `2026-10-21`); mới nhất 2.8.0 (2026-11-10).

## Sources
- https://platform.claude.com/docs/en/api/rate-limits#response-headers (truy cập 2026-11-11)
- https://platform.claude.com/docs/en/api/rate-limits#reaching-your-spend-cap (truy cập 2026-11-11)
- https://platform.claude.com/docs/en/api/errors#http-errors (truy cập 2026-11-11)
- https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python#retries (truy cập 2026-11-11)
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching (truy cập 2026-11-11)
- https://github.com/anthropics/anthropic-sdk-python/blob/main/MIGRATION.md (truy cập 2026-11-11)
- https://pypi.org/project/anthropic/#history (truy cập 2026-11-11)
