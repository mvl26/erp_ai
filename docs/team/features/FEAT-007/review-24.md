Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 24 — FEAT-007 T24

- Diff: `git diff 66fc4afb47f2bc1727f845919304b94f733776d2..c744348` (đầu nhánh task khi merge; merge `fd08310` trên `team/FEAT-007`)
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve (vòng 2); vòng 1 là design-defect, đã có phán quyết (2) và 5c(i) của `design-w0-fixes-2.md`

## Vòng 1 — design-defect

- Range: `66fc4af..c02e355` (1 commit, 2 file, +121/−3), đúng 2 file của touchpoints.
- Bằng chứng của dev: RED `erp_ai.agent.test_routing` `TypeError: decide_route() got an unexpected keyword argument 'due_at'`, `Ran 59 tests in 0.067s FAILED (errors=44)`; GREEN `Ran 59 tests in 0.049s OK`; `erp_ai.tests.test_architecture` `Ran 112 tests in 3.081s OK`.

### Phát hiện

major | STD-DESIGN-3 | design.md:382-383 so với :387 (lộ ra ở erp_ai/agent/routing.py:76-78 → runner.py:528-530) | Câu "hai nơi gọi cũ không đổi hành vi" sai đối với `notes`. Với mặc định `due_field_configured = False` mà thiết kế ghim, nơi gọi không truyền gì bị coi là "chưa cấu hình", nên dòng log của runner cho phiếu B/D nay mang một mục "chưa cấu hình trường Hạn hoàn thành" sai cho tới U4b. Không test nào ghim `notes` mà nơi gọi cũ nhận: `test_existing_rules_kept` chỉ so priority. | Designer chọn một: (a) sửa chữ `design.md:382` thành "priority không đổi; notes của B/D có thêm ghi chú về trường hạn cho tới khi U4b truyền tham số" → mã T24 giữ nguyên, approve. Hoặc (b) đổi mặc định thành `due_field_configured: bool | None = None`, `None` nghĩa là "nơi gọi không nói" → không ghi chú, không ngoại lệ; `tasks.md` T24 `Returns` sửa theo, T24 thêm test: lời gọi kiểu cũ cho B/D không trả ghi chú `due_at`.

minor | — | — | 2 điểm nhỏ: (1) erp_ai/agent/test_routing.py:697: ca "A importance 1, sắp tới hạn bị bỏ qua" mong High, mà mapping của A vốn đã cho High, nên nếu ngoại lệ theo hạn cũng nổ cho A thì test vẫn xanh; dùng mapping có A là Medium. (2) Nhánh `now or now_datetime()` ở routing.py:163 không có test (chấp nhận được theo STD-TEST-6) | tùy dev

### Nơi gọi cũ nhận gì (reviewer đã đọc)

- Priority: không đổi ở mọi nơi gọi (`due_at` là None, và mã cũng đặt None khi chưa cấu hình).
- `notes` cho phiếu B/D: thêm mục `{"field": "due_at", "reason": DUE_FIELD_MISSING_NOTE}`.
  - `runner.py:281` → `_record_route` (`runner.py:528-530`) đưa vào `skipped_fields` của mọi dòng log classify B/D đã áp, cả trên site CÓ cấu hình trường hạn, cho tới khi U4b truyền `due_field_configured` (`design-addendum-1-U4b-U8.md:245`).
  - `write_ticket.py:50` → không lộ (dòng 64 chỉ giữ `ticket_type`, `agent_group`, `priority`).
  - `run_eval.py:198` → không đọc notes. Có ba nơi gọi trong mã sản phẩm, không phải hai.

### Ghi nhận của reviewer

- AC-25 đã làm: B tới hạn trong 24 giờ → ít nhất High (biên đúng 24 giờ là `<=`, quá hạn có tính, 24 giờ + 1 giây không nâng); D có hạn → ít nhất High; dùng `max` theo `_rank` nên Urgent giữ Urgent; [GẤP], F → Low, E → rỗng trả về trước luật mới. Chữ ghi chú đúng `design.md:387`. `d_watcher` chỉ được nhận.
- 18 ca subTest (≥ 14); các đột biến reviewer xét đều làm test đỏ (`<=` → `<`, đảo phép trừ, bỏ qua `now`, bỏ `due_at = None`, ghi chú nổ cho mọi đầu mục).

### Review checklist (10)
1. đạt (điểm thiết kế ở trên) 2. đạt 3. đạt (RED trước; không skip) 4. đạt (`NOW` cố định, `keep_agent_settings`) 5. đạt 6. đạt 7. hợp đồng: keyword-only có mặc định, nơi gọi không vỡ; hành vi: xem finding 8. đạt 9. đạt 10. đạt (`feat(agent): ... (FEAT-007)`)

## Vòng 2 — approve (chấm lại cả range sau phán quyết)

- Range: `66fc4af..c744348` (2 commit, 2 file, +195/−3), đúng touchpoints; commit thứ hai `c02e355..c744348`.
- Bằng chứng của dev: RED trên `c02e355` `Ran 62 tests in 2.741s FAILED (failures=4, errors=6)`: `AttributeError: module 'erp_ai.agent.routing' has no attribute 'as_deadline'`, `TypeError: unsupported operand type(s) for -: 'datetime.date' and 'datetime.datetime'`, `AssertionError: 'due_at' unexpectedly found in ['assignee', 'due_at']`; GREEN `test_routing` `Ran 62 tests in 2.283s OK`, `test_architecture` `Ran 112 tests in 3.436s OK`, `test_run_eval` `Ran 22 tests in 0.696s OK`; `test_runner_routing` trên nhánh task (tech-lead chạy lại riêng sau 4 lần dev dính `QueryDeadlockError`) `Ran 62 tests in 43.041s OK`.
- Kết luận của reviewer: design-defect vòng 1 đã được giải quyết. `routing.py:63` mặc định `due_field_configured: bool | None = None`; `:80` ghi chú chỉ khi `category in ("B", "D") and due_field_configured is False` và đặt `due_at = None` ở đó; ba nơi gọi (`runner.py:281`, `write_ticket.py:50`, `run_eval.py:198`) không truyền tham số mới nên nhận đúng `priority`, `notes` cũ, có `test_old_call_shape_no_due_note` ghim cho 6 đầu mục. `as_deadline` (`routing.py:174-180`) đúng 5c(i), `_priority` gọi một lần trước cả hai phép so. 5c(ii) thuộc đợt 1, không có ở đây. Tám đột biến reviewer lần theo (đổi `is False` thành `not`, bỏ `due_at = None`, date về 00:00, `<=` thành `<`, v.v.) đều có test đỏ.

### Phát hiện

Không có blocker/major.

minor | — | — | 4 điểm nhỏ: (1) `test_old_call_shape_no_due_note` chỉ kiểm không có ghi chú `due_at`, không so cả bộ `notes` với đầu ra cũ; (2) `as_deadline` ném `TypeError` với chuỗi ngày như `"2026-11-15"`, và vì chạy cho cả A, C nên U4b đợt 1 phải truyền date/datetime thật; (3) `TestPriorityExceptions.setUp` gọi `keep_agent_settings` cho hàm thuần; (4) dòng `Returns` của T24 trong `tasks.md` và `design.md:382-387` còn chữ cũ, phán quyết và dòng "Chèn 2" thắng | tùy dev

### Review checklist (10)
1. đạt 2. đạt 3. đạt (RED trên `c02e355`; biên đúng 24 h, 24 h + 1 s, quá hạn, date cuối ngày; không skip) 4. đạt (`now` cố định; test sửa theo phán quyết, lý do trong commit) 5. đạt 6. đạt 7. đạt (tham số mới chỉ theo tên, có mặc định; ba nơi gọi không đổi) 8. đạt 9. đạt 10. đạt (`feat(agent)`, `fix(agent): … (FEAT-007)`)

### Phần kiểm của tech-lead (vòng 2)

- Sau merge `fd08310` (và `0213915` của T41), tech-lead chạy từ worktree `feat-007`: `test_routing` `Ran 62 tests in 0.047s OK` (lần chạy đầu không in dòng kết quả, chạy lại thì có), `test_runner_routing` `Ran 62 tests in 63.426s OK`, `test_run_eval` `Ran 23 tests in 0.565s OK`, `test_architecture` `Ran 112 tests in 3.240s OK`; `cmd.lint`: chỉ nợ nền `erp_ai/test_change_decision.py`.
- Mục "không kiểm được từ diff": kiểu giá trị hạn mà U4b truyền (date, datetime hay chuỗi) và `due_route_kwargs` là việc của đợt 1 → báo team-leader, đưa minor (2) vào đầu vào của `/team:plan` đợt 1. T26 dùng lại `as_deadline`: reviewer của T26 chấm.
- deferred vòng 2: 4 điểm nhỏ ở trên; chữ cũ của `design.md:382-387` (designer).

## Phần kiểm của tech-lead

- Đã đọc `design.md:382` và `:387`: hai câu cùng tồn tại và mâu thuẫn với mặc định `False`; dev làm đúng chữ `:387` và đã tự nêu điểm này trong báo cáo. Tech-lead không chọn (a) hay (b).
- `team/FEAT-007-task-24` @ `c02e355` và worktree của dev giữ nguyên, chưa merge. Task bị chặn theo: T25, T26 (và T51 sau đó).

## Không kiểm được từ diff — chuyển team-leader/designer cùng phán quyết

| Mục | Ghi chú |
|---|---|
| Date so với datetime | AC-24 buộc trường hạn là Date (`test_due_field_must_be_date`), phụ lục (`design-addendum-1-U4b-U8.md:245`) truyền `due_at=<giá trị field_due_date>`. Frappe trả `datetime.date` cho trường Date; `date - datetime` ở routing.py:163 ném TypeError. U4b phải đổi kiểu, và thiết kế cần nói "hạn hôm nay" là 00:00 hay 23:59. |
| Đường `set_classification` (AC-25 "không hạ" từ đầu tới cuối) | Phụ lục (`:33`) không nối `write_ticket.py:50` với tham số hạn. Một lời gọi `set_classification` ở lượt lập luận tính lại priority không có ngoại lệ và ghi đè: phiếu D được bước classify đặt High có thể bị đưa về Medium. |
| `run_eval` lệch runner | Sau U4b, `runner.py:281` truyền thêm 4 tham số còn `run_eval.py:198` thì không: priority của B/D có hạn trong eval sẽ khác runner. |
| Test chưa do reviewer chạy; cả bộ chưa chạy | Dev đã chạy riêng các module của nơi gọi cũ, đều `OK`: `test_runner_routing` 62, `test_agent_runner` 67, `tools.test_write_ticket` 37, `eval.test_run_eval` 22. |

## deferred

- (minor, tùy dev) hai điểm nhỏ ở trên; điểm (1) nên sửa cùng lần làm lại nếu designer chọn (b).
