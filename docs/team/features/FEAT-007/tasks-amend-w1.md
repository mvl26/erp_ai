Feature: FEAT-007
Stage: plan
Author-agent: tech-lead
Date: 2026-11-15
Approved-by:
<!-- Cổng: không có cổng nào trước G5 (`team.py status` 09:18: `planned 66/174`). -->

# FEAT-007 — tasks-amend-w1: một khối dán cuối cùng cho mỗi task của đợt 1 (gom `design-w1-fixes-5.md` … `-10.md` và năm phán quyết `files:` 09:10)

File này KHÔNG sửa `tasks.md`, không sửa file kế hoạch hay thiết kế nào. Tech-lead build dán nó ở đầu vòng 16.

- Nguồn đã gom: `design-w1-fixes-5.md` (T174), `-6.md` (T82 "Chèn 8", T34), `-7.md` (T78, T79, T82, T87), `-8.md` (T72, T80, T81), `-9.md` (T80, T83), `-10.md` (T93, T82, T85, T140); năm phán quyết `files:` của team-leader F-1, F-4, F-9, F-13, F-15 (`docs/team/journal/FEAT-007.pending-2.md`, quyết định 09:10); `preflight-w1.md`; `plan-w1.md`, `plan-w1b.md`.
- Nền: chữ của `tasks.md` đọc lúc 09:21–09:22 ngày 2026-11-15 (174 dòng task, 67 dòng `[x]`), khi vòng build 15 còn chạy; mã ở `team/FEAT-007` @ `caa555a`.
- Mọi khối dưới đây bỏ dòng `progress:` (vòng build giữ dòng đó).
- Nhãn "Chèn 11" là nhãn của lượt gom này: dùng cho năm phán quyết `files:` 09:10 và một câu có điều kiện của `design-w1-fixes-8.md` Điểm 3 mục 3.
- Skill: `/team:plan` (lượt gom, `--insert` không đổi số task). Dòng journal của lượt này không ghi được ở đây (lời giao cấm sửa journal); team-leader ghi.

---

## 1. Cách áp (theo thứ tự)

1. Chờ vòng 15 trả về, không dev nào còn ghi `tasks.md`. Đọc các dòng `progress:` và `git log --oneline develop..team/FEAT-007`; không làm lại task đã tick.
2. Chạy năm phép kiểm chỉ đọc của mục 2 trên đầu `team/FEAT-007` lúc đó và chọn biến thể theo bảng của mục 2.
3. Với từng task theo thứ tự trong `tasks.md`: T34, T174, T72, T74, T75, T78, T79, T80, T81, T82, T83, T85, T87, T89, T92, T93, T140:
   - Task đã `[x]` hoặc đã merge: KHÔNG dán khối; làm theo cột "đã merge" của bảng mục 2 (nếu có dòng cho task đó), ngoài ra không làm gì.
   - Task chưa merge: thay mọi dòng của task, từ dòng tiêu đề `- [ ] T<N> …` tới dòng ngay trước `progress:` (task chưa có `progress:` thì tới dòng ngay trước tiêu đề task kế), bằng khối của mục 3. Dòng `progress:` giữ nguyên chỗ, là dòng cuối của task.
   - Trước khi thay: so các dòng không phải `progress:` của task với chữ Nền (chữ cũ của từng dòng nằm trong các file nguồn và trong khối). Vòng 15 đã đổi một dòng không phải `progress:` của task đó → không dán task đó, ghép tay và ghi một dòng journal.
   - Task đang có nhánh `team/FEAT-007-task-<N>` mở mà chưa merge (kiểm `git branch --list 'team/FEAT-007-task-*'`): vẫn dán khối; phần khác với việc dev đã làm đưa vào lời giao kế của task đó.
4. Thêm một dòng "chèn 11" vào khối tiến độ của `tasks.md`, dẫn file này và sáu file `design-w1-fixes-5.md` … `-10.md`.
5. Kiểm `grep -cE '^- \[[ x]\] T[0-9]+' docs/team/features/FEAT-007/tasks.md` = 174 (lượt này không thêm, không bớt task).
6. Chạy lại phép kiểm của mục 6 trên `tasks.md` đã dán; kết quả phải là: không ID lạ, không vòng, không cặp chưa xếp thứ tự mới nào ngoài các cặp có T126 hoặc T32 đã nêu ở mục 6. Khác → dừng, không gọi dev.
7. Các hàng "Một file, một chủ" của mục 4 thay cho hàng cùng tên của `plan-w1.md`, `plan-w1b.md` khi điều phối (file kế hoạch do lượt lập kế hoạch sau sửa; vòng build giữ thứ tự theo mục 4).
8. Ràng buộc cho mọi lời giao (quyết định 09:18 (b)): T126 không cùng đợt với T78, T79, T82. T82 chạy một mình trong lượt của nó (`plan-w1.md` R-4; nay 11 file). Ghi chú cho lời giao dev ở mục 7.

---

## 2. Phép kiểm trạng thái build (chỉ đọc) và biến thể

Kết quả lúc 09:22 trên `team/FEAT-007` @ `caa555a`: cả năm phép không in dòng nào (T72, T74, T75 chưa merge). Phải chạy lại ở đầu vòng 16.

| # | Lệnh | In ra dòng nào đó | Không in gì |
|---|---|---|---|
| K-72 | `git log --oneline team/FEAT-007 --grep='merge T72 '` | T72 đã merge: không dán khối T72; chạy K-81 | T72 chưa merge: dán khối T72; T81 dùng bản A |
| K-74 | `git log --oneline team/FEAT-007 --grep='merge T74 '` (đối chứng: `git grep -c 'def enter_agent_session' team/FEAT-007 -- erp_ai/agent/authority.py`) | T74 đã merge: không dán khối T74; F-1 hết hiệu lực theo chính quyết định 09:10 ("chỉ có hiệu lực nếu task chưa merge khi vòng 16 mở"); báo team-leader trạng thái của `TestRunner::test_missing_agent_user_stops` | T74 chưa merge: dán khối T74 |
| K-75 | `git log --oneline team/FEAT-007 --grep='merge T75 '` (đối chứng: `git grep -c 'comment_name' team/FEAT-007 -- erp_ai/agent/queue.py`) | T75 đã merge: không dán khối T75; chạy K-F4 | T75 chưa merge: dán khối T75 (có F-4); T80 dùng bản a |
| K-F4 (chỉ khi K-75 in ra dòng) | `git grep -n 'job.get("comment_name")' team/FEAT-007 -- erp_ai/tests/test_ticket_panel.py` | F-4 đã có trong mã: T80 dùng bản a | F-4 chưa có: T80 dùng bản b (nhận `test_ticket_panel.py`) |
| K-81 (chỉ khi K-72 in ra dòng; lệnh của `design-w1-fixes-8.md` Điểm 3 mục 3) | `git grep -n '"do_tin_cay_pct"' team/FEAT-007 -- erp_ai/agent/test_agent_runner.py erp_ai/agent/test_runner_routing.py erp_ai/eval/test_run_eval.py` | Đọc giá trị từng dòng: mọi giá trị ≥ 70 → T81 bản A. Có giá trị < 70 trong `test_runner_routing.py` → T81 bản B. Có giá trị < 70 trong `test_agent_runner.py` → dán thêm dòng "Chèn 11 có điều kiện" của T80. Giá trị trong `eval/test_run_eval.py` không quyết định gì | T72 merge mà không có khóa: trái dòng T72, dừng và báo team-leader |

Năm phán quyết `files:` 09:10 khi task chủ đã merge trước vòng 16: F-1 (T74) hết hiệu lực, báo team-leader; F-4 (T75) chuyển sang T80 (bản b); F-9 (T82), F-13 (T92), F-15 (T93): hết hiệu lực, báo team-leader. Lượt gom này không đặt chủ mới cho chúng.

---

## 3. Khối dán

### T34 — nguồn: `design-w1-fixes-6.md` Điểm 2 (dòng "Chèn 2" giữ)

```
- [ ] T34 — Việc quét 15 phút xếp lại phiếu bị lỡ [migrate] — files: erp_ai/agent/missed_scan.py, erp_ai/agent/test_missed_scan.py, erp_ai/hooks.py — test: erp_ai/agent/test_missed_scan.py — depends: T33, T40
  - Tiêu chí: AC-16 (lịch 15 phút; quét hai lần → một job mỗi phiếu, NFR-3); ADR-033 QĐ 2; D-17 (1 dòng logger mỗi lần chạy); D-16 trần ứng viên (`design-w1-fixes-6.md` Điểm 2).
  - Chèn 2 (`design-w0-fixes-2.md` 5d): thứ tự chủ của `erp_ai/hooks.py` là T40 → T34 → T44; T34 không còn chờ T44 và tự tạo khóa `cron` trong `scheduler_events` (T44 thêm 3 dòng vào khóa đó sau). `depends:` thêm T40 vì chung `hooks.py`.
  - Receives: `find_missed_tickets`, `CANDIDATES_SQL`, `SCAN_BATCH` (T33); `queue.enqueue_agent_run(ticket, trigger)`, `TRIGGER_TICKET_INSERT`, `policy.is_enabled()`, `LOGGER_NAME` của `erp_ai.constants` (hiện có); `hooks.py` sau T40; trần ứng viên theo `design-w1-fixes-6.md` Điểm 2.
  - Returns: `scan_missed_tickets(now: datetime | None = None) -> None`; dòng `"*/15 * * * *": ["erp_ai.agent.missed_scan.scan_missed_tickets"]` trong `hooks.py`. Trần ứng viên (`design-w1-fixes-6.md` Điểm 2, bổ sung D-16): hằng `SCAN_CANDIDATE_LIMIT = 1000`; `CANDIDATES_SQL` đổi `order by t.creation asc, t.name asc` thành `order by t.creation desc, t.name desc` và thêm `limit %(limit)s`, tham số `"limit": SCAN_CANDIDATE_LIMIT` đọc lúc gọi; `find_missed_tickets` duyệt `reversed(candidates)`, điều kiện lọc, chỗ dừng `SCAN_BATCH`, chữ ký và thứ tự đầu ra không đổi; khi `len(candidates) == SCAN_CANDIDATE_LIMIT` ghi đúng một dòng `frappe.logger(LOGGER_NAME).warning("missed_scan: chạm trần %s ứng viên, phiếu cũ hơn không được xét", SCAN_CANDIDATE_LIMIT)`. Không cắt theo tuổi phiếu (AC-16 không có giới hạn tuổi), không lọc nhóm loại trừ/opt-out trong SQL (ADR-003).
  - Expect: `TestMissedScan::test_two_scans_one_job_per_ticket`, `::test_agent_disabled_noop`, `::test_cron_declared_every_15_minutes` xanh. Trần ứng viên, test viết trước, đỏ trên mã T33: `::test_candidate_window_keeps_the_newest` (vá `SCAN_CANDIDATE_LIMIT` = 3, bốn phiếu đủ điều kiện a < b < c < d theo `creation` → `_found` = [b, c, d]; trên mã T33 ra [a, b, c, d]), `::test_old_refused_tickets_do_not_starve_a_new_one` (vá trần = 3, năm phiếu opt-out cũ hơn và một phiếu mới đủ điều kiện e, bọc `policy.can_send_ticket` bằng `wraps` → `_found` = [e] và `can_send_ticket` được gọi đúng 3 lần; trên mã T33 gọi 6 lần), `::test_warns_once_when_candidate_limit_reached` (vá trần = 3 và vá `missed_scan.frappe.logger`: ba phiếu ứng viên → `warning` gọi đúng một lần, chữ có `"chạm trần"`; hai phiếu → không gọi). Tám test của T33 (`test_constants`, `test_seven_ticket_kinds`, `test_runs_below_daily_limit_still_found`, `test_failed_run_requeued`, `test_predicted_category_on_other_entry_type_does_not_count`, `test_grace_edge_exactly_five_minutes`, `test_no_enabled_at_noop`, `test_batch_limit_oldest_first`) không sửa chữ và còn xanh. `cmd.test_one` xanh cả file `erp_ai/agent/test_missed_scan.py` và `erp_ai/tests/test_architecture.py`.
```

### T174 — nguồn: `design-w1-fixes-5.md` (làm tiếp trên `team/FEAT-007-task-174` @ `d1e89f3`; BASE của vòng review kế `ce696e161d9d9a208ae2e4d46d6c4598b819d61c`; vòng 2 trong trần `max_rework` = 3)

```
- [ ] T174 — Hàm che: phần đuôi sau giá trị đã che ở R-3 thuộc cùng giá trị trần (K-7) — files: erp_ai/agent/redact.py, erp_ai/agent/test_redact.py — test: erp_ai/agent/test_redact.py — depends: T120
  - Tiêu chí: NFR-6, AC-46, AC-50; ADR-034 QĐ 2; `review-120.md:45`; `review-174.md:28-29`; `design-w1-fixes-5.md` (K-4b mới, K-7 thay bản của `design-w1-fixes-2.md:95`, K-4a thêm một câu). Làm tiếp trên `team/FEAT-007-task-174` @ `d1e89f3`, không làm lại. Chỉ sửa `_mask_key_values` và thêm `_WORD_START`, `_NOT_WORD_CHAR`, `_secret_value_end`; không đổi `SECRET_PATTERNS`, `SECRET_WORDS`, `MASK`, `is_secret_key`, chữ ký `redact_secrets`, regex `_KEY_CANDIDATE`, `_KEY_VALUE`, `_BARE_VALUE_STEP`, `_BARE_VALUE_TAIL`.
  - Receives: `redact.py` sau T120: `_KEY_CANDIDATE`, `_KEY_VALUE` (nhánh trần K-4 với nhìn trước (a)/(b)/(c)), `_mask_key_values`, `is_secret_key`, `MASK`.
  - Returns: không tên công khai mới. Giữ phần `d1e89f3` (`_BARE_VALUE_STEP` dùng chung cho `_KEY_VALUE` và `_BARE_VALUE_TAIL`). Thêm riêng tư `_WORD_START = re.compile(r"(?<![\w-])[\w-]")`, `_NOT_WORD_CHAR = re.compile(r"[^\w-]")` và `_secret_value_end(text: str, start: int, end: int) -> int` đúng chữ ở `design-w1-fixes-5.md` mục "Mã đề xuất" (điểm dừng = `MASK` đầu tiên bắt đầu trước `end`, hoặc đầu ứng viên `_KEY_CANDIDATE.match` đầu tiên ở một `_WORD_START` trong khoảng có `is_secret_key(name)`; lùi qua ký tự `_NOT_WORD_CHAR` nhưng không qua `start`; không có điểm dừng → `end`; docstring không viết `\w` trong chuỗi thường). Trong `_mask_key_values`: nhánh `MASK` với tên bí mật đặt `position = _secret_value_end(text, position, _BARE_VALUE_TAIL.match(text, position).end())`; nhánh trần với tên bí mật: `end = _secret_value_end(text, position, value.end())`, `end > position` → thêm `MASK`, `position = end`; `end == position` → không thêm gì, quét tiếp từ cuối ứng viên. Nhánh nháy kép, nháy đơn, tên không bí mật: như cũ.
  - Expect: bốn test mới trong `TestRedact`: `::test_value_stops_before_next_secret_key` (`password=sk-ant-FAKE|api_key: hunter2` → `password={MASK}|api_key: {MASK}`; `password=sk-ant-FAKE.pwd = hunter2` → `password={MASK}.pwd = {MASK}`; `password=sk-ant-FAKE&tailFAKE|api_key: hunter2` → `password={MASK}|api_key: {MASK}`; `password=sk-ant-FAKE|my api key: hunter2` → `password={MASK}|my api key: {MASK}`; `password=abc|api_key: hunter2` → `password={MASK}|api_key: {MASK}`; `password=api_key: hunter2` → `password=api_key: {MASK}`; mỗi ca kiểm thêm `"hunter2" not in` kết quả) và `::test_value_stops_before_mask` (`password=sk-ant-A&sk-ant-B` → `password={MASK}&{MASK}`; `password=sk-ant-FAKE&tailFAKE.sk-ant-B` → `password={MASK}.{MASK}`; `password=x&sk-ant-FAKE` → `password={MASK}&{MASK}`; mỗi ca kiểm thêm `"che] che]" not in`) đỏ trước trên `d1e89f3` (đúng 9 subtest, đầu ra không lọc qua `grep`/`tail`) rồi xanh; `::test_non_secret_key_inside_value_stays_value` (test ghim, xanh ngay là đúng, ghi lý do trong progress: `password=sk-ant-FAKE|user:bob` → `password={MASK}`; `password=ab|user:bob` → `password={MASK}`; `password=sk-ant-FAKE|"api_key": "hunter2"` → `password={MASK}"api_key": "{MASK}"`) và `::test_secret_value_cut_stays_linear` (test ghim K-8: `"password=" + "|user:" * 30_000`, `"pwd=a|x " * 25_000`, `"password=" + "a." * 50_000 + "api_key: z"`; mỗi ca dưới 10 s, kết quả bắt đầu bằng `password={MASK}` hoặc `pwd={MASK}`, không chứa `a|x`, không chứa `api_key: z`); `test_pattern_masked_value_tail_masked` (7 ca) và `test_pattern_masked_value_tail_stops_like_bare_value` (6 ca) của `7c11873` giữ xanh, không đổi khẳng định; mọi test `TestRedact` cũ giữ xanh, gồm `test_value_patterns_run_before_key_scan`, `test_list_separator_*`, `test_key_value_rules`, `test_long_run_without_secret_untouched`, `test_every_pattern_is_python_310_syntax`. `cmd.test_one` xanh cho `erp_ai/agent/test_redact.py` và `erp_ai/agent/test_knowledge.py`.
```

### T72 — nguồn: `design-w1-fixes-8.md` Điểm 3 (chỉ dán khi K-72 không in gì; tiêu đề, Receives, Returns không đổi)

```
- [ ] T72 — Độ tin cậy số `do_tin_cay_pct` của bước phân loại [migrate] — files: erp_ai/agent/classification.py, erp_ai/agent/prompts.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json, erp_ai/agent/test_classification.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/test_runner_routing.py, erp_ai/eval/test_run_eval.py — test: erp_ai/agent/test_classification.py — depends: T56, T19, T64, T67, T125
  - Tiêu chí: AC-22 (D-14); `U1.md:249-253`; C-4 (`w1a.md:58`): khóa mới của `CLASSIFY_PROMPT` và phần tử `"do_tin_cay_pct"` của `PROMPT_REQUIRED_MARKERS["classify"]` cùng một commit. Chín file vì C-4 buộc cùng commit; ba file test cuối chỉ thêm `"do_tin_cay_pct": 100` ngay sau `"do_tin_cay"` vào mọi JSON stub có `"dau_muc"` có sẵn (`design-w1-fixes-8.md` Điểm 3: 100 không dưới ngưỡng nào trong 0..100, test không phụ thuộc ngưỡng của site dùng chung, STD-TEST-6). `erp_ai_setting.json` (`design-w1-fixes-4.md` Điểm 2): chữ mô tả `prompt_override_classify` thay nguyên văn theo Điểm 2 (12 khóa, 367 ký tự), `"modified"` tăng; `"do_tin_cay_pct"` đứng ngay sau `"do_tin_cay"` trong `PROMPT_REQUIRED_MARKERS["classify"]` và `PROMPT_PARTS["classify"]` của test, cùng commit. Chuỗi chủ `erp_ai_setting.json`: T64 → T125 → T72.
  - Receives: `PROMPT_REQUIRED_MARKERS` (T19).
  - Returns: `Classification.confidence_pct: int`; `CONFIDENCE_PCT_MIN = 0`, `CONFIDENCE_PCT_MAX = 100`; `parse_classification` từ chối thiếu, `bool`, ngoài 0..100, số thực; khóa nhãn `do_tin_cay` giữ.
  - Expect: `TestConfidencePct::test_parse_accepts_0_to_100`, `::test_parse_rejects_missing_bool_negative_over_100_float`; test "prompt dựng sẵn qua kiểm mục bắt buộc" của T19 xanh; `cmd.migrate` trước `cmd.test_one`; `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestPromptOverrides::test_required_markers_match_design` đỏ trước (thêm mục vào `PROMPT_PARTS` của test khi nguồn chưa có) rồi xanh, cùng `::test_builtin_prompts_pass_required_markers`, `::test_markers_need_their_exact_form` không đổi khẳng định; `erp_ai/tests/test_doctype_descriptions.py` xanh không sửa (mô tả ≤ 400, đủ bốn cụm); `test_agent_runner`, `test_runner_routing`, `eval/test_run_eval` giữ xanh; mọi `"do_tin_cay_pct"` trong ba file đó bằng 100. Chèn 6, CI-6 (`arch-impact-chg-002.md:95`): `test_prompts.py`, `test_agent_runner.py` không chép chữ của `CHANGE_TOOLS_BLOCK` ngoài dòng neo P-1.
```

Ghi chú: sau khối này chuỗi chủ `erp_ai_setting.json` kéo dài thành T64 → T125 → T72 → T79 (mục 4); câu "Chuỗi chủ … T64 → T125 → T72" ở Tiêu chí là chữ cũ của T72, không nguồn nào bảo sửa.

### T74 — nguồn: F-1 (quyết định 09:10; chỉ dán khi K-74 không in gì)

```
- [ ] T74 — `authority.enter_agent_session`: một chỗ chuyển phiên — files: erp_ai/agent/authority.py, erp_ai/agent/test_authority.py, erp_ai/agent/runner.py, erp_ai/tests/test_architecture.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_authority.py — depends: T73, T71, T67, T72
  - Tiêu chí: ADR-033 QĐ 1; `U1.md:194-203`, `:258`, `:264`.
  - Chèn 11 (F-1 của `preflight-w1.md:22`; phán `files:` của team-leader, quyết định 09:10 ở `docs/team/journal/FEAT-007.pending-2.md`; file thứ năm của `files:`): T74 thêm `erp_ai/agent/test_agent_runner.py` vào `files:`, chỉ sửa đích vá `AGENT_USER` trong `TestRunner::test_missing_agent_user_stops` từ `runner` sang `authority` (dòng `:177` ở `team/FEAT-007` @ `caa555a`: `patch.object(runner, "AGENT_USER", …)`), không đổi khẳng định nào (`:182`, `:184` giữ); `cmd.test_one` xanh cả file `erp_ai/agent/test_agent_runner.py`. Chuỗi chủ `test_agent_runner.py`: … T72 → T74 → T80 …, nên `depends:` thêm T72. Vì: test ngoài `files:` ghim hình dạng cũ, cách sửa không có lựa chọn thiết kế. Sai thì: gỡ file khỏi `files:` và chuyển designer.
  - Receives: thân chuyển phiên hiện có của `runner._run` bước (a).
  - Returns: `authority.TITLE_WRONG_USER`, `enter_agent_session() -> bool`; `runner._run` bước (a) thành `if not authority.enter_agent_session(): return`; tên `runner.TITLE_WRONG_USER` còn (import lại).
  - Expect: `TestEnterAgentSession::test_switches_to_agent`, `::test_disabled_agent_refused_and_logged`, `::test_missing_agent_refused_and_logged`; `erp_ai/tests/test_architecture.py::test_set_user_agent_only_in_enter_agent_session` xanh.
```

### T75 — nguồn: F-4 (quyết định 09:10; chỉ dán khi K-75 không in gì. K-75 in ra dòng → không dán, F-4 sang T80 bản b)

```
- [ ] T75 — Job `@ai` mang tên comment kích hoạt — files: erp_ai/agent/queue.py, erp_ai/handlers.py, erp_ai/agent/runner.py, erp_ai/agent/test_queue.py, erp_ai/tests/test_handlers.py, erp_ai/tests/test_ticket_panel.py — test: erp_ai/agent/test_queue.py — depends: T74
  - Tiêu chí: AC-13; `U1.md:211-212`, `:257`; A-U1-3 (`job_id` giữ).
  - Chèn 11 (F-4 của `preflight-w1.md:26`; phán `files:` của team-leader, quyết định 09:10; file thứ sáu của `files:`): T75 thêm `erp_ai/tests/test_ticket_panel.py` vào `files:`, chỉ sửa dòng chạy lại job trong `_decision` (`:732` ở `team/FEAT-007` @ `aedc360`: `runner.run_for_ticket(job["ticket_name"], job["trigger"])`) để truyền `job.get("comment_name")`; không đổi khẳng định nào; `cmd.test_one` xanh cả file `erp_ai/tests/test_ticket_panel.py`. Chuỗi chủ `test_ticket_panel.py`: T175 (đã tick) → T75. Vì: test ngoài `files:` ghim hình dạng cũ, cách sửa không có lựa chọn thiết kế. Sai thì: gỡ file khỏi `files:` và chuyển designer.
  - Receives: `enqueue_agent_run(ticket_name, trigger)` hiện có.
  - Returns: `enqueue_agent_run(ticket_name, trigger, comment_name=None) -> bool` (`TRIGGER_COMMENT_MENTION` mà `comment_name` rỗng → `ValueError`); `run_for_ticket(ticket_name, trigger, comment_name=None)` truyền xuống `_run` (chưa dùng; dùng ở T80); `handlers.comment_after_insert` truyền `comment_name=doc.name`.
  - Expect: `TestEnqueue::test_comment_mention_job_carries_comment_name`, `::test_comment_mention_without_comment_name_raises`; `erp_ai/tests/test_handlers.py::TestCommentHook::test_mention_enqueues_with_comment_name` xanh.
```

### T78 — nguồn: `design-w1-fixes-7.md` Điểm 1 (chỉ dòng Expect thêm đuôi)

```
- [ ] T78 — `core_prompt`: quy tắc 6 mới, GIỚI HẠN ghép theo cờ — files: erp_ai/agent/prompts.py, erp_ai/agent/test_prompts.py — test: erp_ai/agent/test_prompts.py — depends: T72
  - Tiêu chí: AC-6, AC-66; `U1.md:221-245` với các dòng bị `w1.md:76-83` thay (U1-1..U1-4, U1-6, U1-8). `erp_ai/agent/test_prompts.py` là file mới.
  - Receives: chuỗi `CORE_PROMPT` hiện có.
  - Returns: `core_prompt(*, change_tools=False, site_admin_tools=False, unrestricted_tools=False, act_now=False, ask_only=False) -> str`; `CORE_PROMPT = core_prompt()`; hằng `RULE_6_ACT`, `RULE_6_ASK`, `NO_OK_APPROVAL`; `PROMPT_CONFLICT_PAIRS` gồm P-1..P-5, P-7, P-8, P-9. Khối VIẾT COMMENT chưa đổi ở task này (T79).
  - Expect: `TestCorePrompt::test_no_conflict_pair_in_any_flag_combination`, `::test_no_ok_approval_in_every_combination`, `::test_default_core_prompt_keeps_rules_1_5_and_limits` (phần quy tắc 6) xanh. Chèn 6, CI-6 (`arch-impact-chg-002.md:95`): `test_prompts.py`, `test_agent_runner.py` không chép chữ của `CHANGE_TOOLS_BLOCK` ngoài dòng neo P-1. `design-w1-fixes-7.md` Điểm 1: T78 không chạm `build_reason_system` (vẫn ghép hằng `CORE_PROMPT`; nối cờ ở T79); `erp_ai/agent/test_classification.py` và `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` xanh không sửa một dòng (chạy `cmd.test_one` cho cả hai file).
```

### T79 — nguồn: `design-w1-fixes-7.md` Điểm 1, Điểm 3 (sáu file, `[migrate]`)

```
- [ ] T79 — Khối VIẾT COMMENT mới, `ASK_ONLY_BLOCK`, mỗi khối đúng một cờ [migrate] — files: erp_ai/agent/prompts.py, erp_ai/agent/test_prompts.py, erp_ai/agent/test_classification.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json, erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — test: erp_ai/agent/test_prompts.py — depends: T78
  - Tiêu chí: AC-6, AC-65 (a), AC-23 `[changed]`; `U1.md:217-229`; `w1.md:80` (U1-5). Hai phép suy ở `prompts.py:328,330` còn giữ ở task này (xóa ở T82). `design-w1-fixes-7.md` Điểm 1 và Điểm 3: T79 nối `core_prompt(**cờ)` vào `build_reason_system` (hai phép suy giữ); ba test `test_reason_system_with_*` của `test_classification.py` đổi mốc so sánh sang `core_prompt(<cờ>)`; mục bắt buộc `reasoning` còn ba (`**Nhận định:**`, `**Căn cứ:**`, `**Hướng xử lý:**`) ở `PROMPT_REQUIRED_MARKERS` và `PROMPT_PARTS` của test, chữ mô tả `prompt_override_reasoning` thay nguyên văn (306 ký tự), `"modified"` tăng, cùng commit với việc bỏ dòng `**Cần ai quyết:** nếu có.`; ghi đè `reasoning` đã lưu giữ nguyên, không patch. Sáu file vì bỏ dòng ở prompt và bỏ mục ở phép kiểm phải cùng commit. Chuỗi chủ `erp_ai_setting.json`: T64 → T125 → T72 → T79; `erp_ai_setting.py`, `test_erp_ai_setting.py`: … → T64 → T72 → T79 → T87 → T124; `test_classification.py`: T72 → T79 → T82.
  - Receives: `core_prompt` (T78).
  - Returns: `build_reason_system(prompt_digest, routing_table="", *, change_tools=False, site_admin_tools=False, unrestricted_tools=False, act_now=False, ask_only=False) -> list[dict]`, phần lõi là `core_prompt(**năm cờ)`, `ACT_NOW_BLOCK` khi `act_now` hoặc một trong ba cờ công cụ, `SITE_ADMIN_TOOLS_BLOCK` khi `site_admin_tools and not unrestricted_tools` (hai phép suy xóa ở T82), `ASK_ONLY_BLOCK` khi `ask_only`, đứng sau `ACT_NOW_BLOCK`; `ASK_ONLY_BLOCK`; khối VIẾT COMMENT theo U1-5 (bỏ dòng "Cần ai quyết"); `PROMPT_REQUIRED_MARKERS["reasoning"] == ("**Nhận định:**", "**Căn cứ:**", "**Hướng xử lý:**")`; mô tả `prompt_override_reasoning` theo `design-w1-fixes-7.md` Điểm 3.
  - Expect: `TestReasonSystem::test_each_block_present_iff_its_flag` (phần `ask_only`), `TestCorePrompt::test_default_core_prompt_keeps_rules_1_5_and_limits` (phần VIẾT COMMENT) xanh. Chèn 6, CI-6 (`arch-impact-chg-002.md:95`): `test_prompts.py`, `test_agent_runner.py` không chép chữ của `CHANGE_TOOLS_BLOCK` ngoài dòng neo P-1. `cmd.migrate` trước `cmd.test_one`; `erp_ai/agent/test_classification.py` xanh cả file, ba test `test_reason_system_with_*` đỏ trước (mốc `core_prompt(<cờ>)` khi lõi còn là `CORE_PROMPT`) rồi xanh; `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestPromptOverrides::test_required_markers_match_design`, `::test_builtin_prompts_pass_required_markers`, `::test_missing_markers_listed_in_constant_order`, `::test_missing_marker_blocked_each_part` xanh, `::test_reasoning_override_with_retired_marker_still_saves` mới xanh; `erp_ai/tests/test_doctype_descriptions.py` xanh không sửa (306 ≤ 400, đủ bốn cụm).
```

### T80 — nguồn: khối của `design-w1-fixes-8.md` (F-5, F-6, F-7 mục 2) + F-3 của `design-w1-fixes-9.md` Điểm 1 + F-4 nếu T75 đã merge

Bản a (K-75 không in gì, hoặc K-F4 in ra dòng): sáu file.

```
- [ ] T80 — Runner dựng context từ `policy` và `run_instructor` — files: erp_ai/agent/runner.py, erp_ai/agent/authority.py, erp_ai/agent/test_authority.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/changes/test_result_comment.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/test_agent_runner.py — depends: T75, T77, T72, T69
  - Tiêu chí: AC-13 (đầu-cuối), AC-22 (lần chạy không tạo phiếu); `U1.md:259-260`, `:207`; `design-w1-fixes-8.md` Điểm 1, Điểm 2, Điểm 3 mục 2; F-3 theo `design-w1-fixes-9.md` Điểm 1. Lần chạy tạo phiếu ở T80: `category=None`, `below_threshold=False` (chuyển tiếp, T81 thay; không test nào ghim). `RunnerTestBase.setUp` vá `policy.latest_classification` trả `SEEDED_CLASSIFICATION = (f"{PREFIX}category", 100)` và đặt `confidence_threshold=policy.DEFAULT_CONFIDENCE_THRESHOLD` (STD-TEST-6); không sửa `test_runner_status.py`, `test_runner_routing.py`.
  - Receives: T66–T69, T73, T75, T76; `policy.latest_classification`, `policy.confidence_threshold`, `policy.is_below_confidence`, `policy.main_path_level`, `policy.DEFAULT_CONFIDENCE_THRESHOLD` (T69); `ASK_TOOL_NAMES` (T77).
  - Returns: `_run` bước (e) và context theo `U1.md:259-260` (lần chạy không tạo phiếu đọc `latest_classification`; lần chạy tạo phiếu `category=None`, `below_threshold=False`); xóa `authority.latest_instructor` và test `test_latest_instructor_prefers_latest_comment_then_owner` (lý do trong commit: ADR-030 QĐ 6, NFR-8); `test_agent_runner.py`: hằng `SEEDED_CLASSIFICATION`, `self.latest_classification`, `self.real_latest_classification` trong `RunnerTestBase.setUp`. Mọi chỗ khác gọi hàm đã xóa đổi sang `run_instructor`, không đổi khẳng định nào khác: `test_result_comment.py:341` → `self.assertIsNone(authority.run_instructor(self.ticket, TRIGGER_COMMENT_MENTION, comment))`, `:350` → `self.assertEqual(authority.run_instructor(self.ticket, TRIGGER_COMMENT_MENTION, human), INSTRUCTOR)`, thêm `TRIGGER_COMMENT_MENTION,` sau `ROLE_INSTRUCTOR,` trong khối import `erp_ai.constants` (`:25`); `test_authority.py:163` → `self.assertIsNone(authority.run_instructor(self.ticket_p, TRIGGER_COMMENT_MENTION, name))`, `:203` → `self.assertIsNone(authority.run_instructor(self.ticket_p, TRIGGER_COMMENT_MENTION, legacy.name))`; `test_agent_runner.py`: mọi `patch.object(authority, "latest_instructor", return_value=X)` → `patch.object(authority, "run_instructor", return_value=X)`, giữ `return_value` (dòng số đo ở `team/FEAT-007` @ `caa555a`).
  - Expect: `TestRunnerGrant::test_plain_user_mention_after_instructor_gets_no_write_tools` (khẳng định trên `task_write`, `change_propose`, `site_admin`, với mặc định trên ngưỡng), `::test_comment_run_reads_latest_classification_of_its_ticket`, `::test_comment_run_below_threshold_from_classify_row_is_ask_only` (dòng `classify` 69, ngưỡng 70), `::test_comment_run_at_threshold_from_classify_row_gets_ticket_write` (dòng 70) xanh; `erp_ai/tests/test_architecture.py::test_authority_has_no_comment_scan_for_instructor` xanh; `erp_ai/agent/test_runner_status.py` (gồm `TestRunnerStatus::test_whole_turn_waits_before_its_first_tool`) và `erp_ai/agent/test_runner_routing.py` (gồm `TestRoutingInjection::test_ticket_text_does_not_steer_route`) xanh không sửa. Đỏ F-3: xóa `latest_instructor` trước khi sửa `test_result_comment.py` → `cmd.test_one` của file đó ra `AttributeError: module 'erp_ai.agent.authority' has no attribute 'latest_instructor'`; sửa hai khẳng định → xanh. `cmd.test_one` xanh cả file: `erp_ai/agent/changes/test_result_comment.py`, `erp_ai/agent/test_authority.py`, `erp_ai/agent/test_agent_runner.py`. Ngoài `erp_ai/tests/test_architecture.py`, `git grep -n latest_instructor -- '*.py'` trên nhánh task ra 0 dòng.
```

Bản b (K-75 in ra dòng VÀ K-F4 không in gì): bảy file. Dùng khối bản a, thay dòng tiêu đề bằng dòng thứ nhất dưới đây và chèn dòng "Chèn 11" ngay sau dòng Tiêu chí.

```
- [ ] T80 — Runner dựng context từ `policy` và `run_instructor` — files: erp_ai/agent/runner.py, erp_ai/agent/authority.py, erp_ai/agent/test_authority.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/changes/test_result_comment.py, erp_ai/tests/test_ticket_panel.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/test_agent_runner.py — depends: T75, T77, T72, T69
  - Chèn 11 (F-4 của `preflight-w1.md:26`; phán `files:` của team-leader, quyết định 09:10, vế "T75 đã merge thì chuyển sang T80"; file thứ bảy của `files:`): T80 thêm `erp_ai/tests/test_ticket_panel.py` vào `files:`, chỉ sửa dòng chạy lại job trong `_decision` (`:732` ở `team/FEAT-007` @ `aedc360`: `runner.run_for_ticket(job["ticket_name"], job["trigger"])`) để truyền `job.get("comment_name")`; không đổi khẳng định nào; `cmd.test_one` xanh cả file `erp_ai/tests/test_ticket_panel.py`. Chuỗi chủ `test_ticket_panel.py`: T175 (đã tick) → T80. Sai thì: gỡ file khỏi `files:` và chuyển designer.
```

Chèn 11 có điều kiện (cả hai bản; CHỈ dán, ngay sau dòng Tiêu chí, khi K-72 in ra dòng và K-81 thấy giá trị < 70 trong `erp_ai/agent/test_agent_runner.py`):

```
  - Chèn 11 (`design-w1-fixes-8.md` Điểm 3 mục 3 (B); T72 đã merge với stub dưới 70): T80 đổi mọi `"do_tin_cay_pct"` của stub trong `erp_ai/agent/test_agent_runner.py` thành 100 (T80 sở hữu file, không đổi `files:`), không đổi khẳng định nào.
```

### T81 — nguồn: `design-w1-fixes-8.md` Điểm 2, Điểm 3 (chọn A hoặc B theo K-72, K-81)

Bản A (K-72 không in gì, hoặc K-81 không thấy giá trị < 70 trong `test_runner_routing.py`):

```
- [ ] T81 — Lần tạo phiếu: context sau phân loại, dưới ngưỡng không định tuyến — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T80
  - Tiêu chí: AC-22; `U1.md:261-262`; C-5 (`w1a.md:59`); `design-w1-fixes-8.md` Điểm 2, Điểm 3. Xóa nhánh chuyển tiếp `below_threshold=False` của T80: lần chạy tạo phiếu dựng context với `category=None, pct=None` qua cùng `policy.is_below_confidence`, rồi `dataclasses.replace` sau phân loại, trước `_route`. Ngưỡng 70 của `RunnerTestBase.setUp` (T80); stub có sẵn mang `do_tin_cay_pct` 100 (T72).
  - Receives: `Classification.confidence_pct` (T72), `is_below_confidence` (T69); `RunnerTestBase` có `confidence_threshold=70` (T80).
  - Returns: `_classify` trả `(proceed: bool, classification, context)`; `_run` dùng `context` trả về cho `_reason`; `_route` chỉ gọi khi `not context.below_threshold`; dòng `classify` ghi `predicted_confidence_pct`; `runner.py` không còn nhánh `TRIGGER_TICKET_INSERT` gán `below_threshold` thẳng.
  - Expect: `TestRunnerGrant::test_low_confidence_insert_skips_routing_writes` (stub `do_tin_cay_pct` 69, ngưỡng 70: không `apply_route`, `applied` 0, dòng `classify` có `predicted_confidence_pct` 69), `::test_insert_at_threshold_routes_and_writes` (stub 70: `_route` chạy, `predicted_confidence_pct` 70) xanh; `erp_ai/agent/test_runner_routing.py` (gồm `:252-270`, `:578-590`, `:694-705`, `TestRoutingInjection::test_ticket_text_does_not_steer_route`) và `erp_ai/agent/test_runner_status.py` xanh không sửa.
```

Bản B (K-72 in ra dòng VÀ K-81 thấy giá trị < 70 trong `test_runner_routing.py`). Câu "Chuỗi chủ" đã ghép với F-13 (xem mục 5, L-4):

```
- [ ] T81 — Lần tạo phiếu: context sau phân loại, dưới ngưỡng không định tuyến — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/test_runner_routing.py — test: erp_ai/agent/test_agent_runner.py — depends: T80
  - Tiêu chí: AC-22; `U1.md:261-262`; C-5 (`w1a.md:59`); `design-w1-fixes-8.md` Điểm 2, Điểm 3 (bản B). Xóa nhánh chuyển tiếp `below_threshold=False` của T80: lần chạy tạo phiếu dựng context với `category=None, pct=None` qua cùng `policy.is_below_confidence`, rồi `dataclasses.replace` sau phân loại, trước `_route`. Ngưỡng 70 của `RunnerTestBase.setUp` (T80). `test_runner_routing.py`: chỉ đổi mọi `"do_tin_cay_pct"` của stub thành 100, cùng commit với mã `_route` có điều kiện; không đổi khẳng định nào. Chuỗi chủ `test_runner_routing.py`: T72 → T81 → T92 → T108.
  - Receives: `Classification.confidence_pct` (T72), `is_below_confidence` (T69); `RunnerTestBase` có `confidence_threshold=70` (T80).
  - Returns: `_classify` trả `(proceed: bool, classification, context)`; `_run` dùng `context` trả về cho `_reason`; `_route` chỉ gọi khi `not context.below_threshold`; dòng `classify` ghi `predicted_confidence_pct`; `runner.py` không còn nhánh `TRIGGER_TICKET_INSERT` gán `below_threshold` thẳng; mọi `"do_tin_cay_pct"` trong `test_runner_routing.py` bằng 100.
  - Expect: `TestRunnerGrant::test_low_confidence_insert_skips_routing_writes` (stub `do_tin_cay_pct` 69, ngưỡng 70: không `apply_route`, `applied` 0, dòng `classify` có `predicted_confidence_pct` 69), `::test_insert_at_threshold_routes_and_writes` (stub 70: `_route` chạy, `predicted_confidence_pct` 70) xanh; `erp_ai/agent/test_runner_routing.py` (gồm `:252-270`, `:578-590`, `:694-705`, `TestRoutingInjection::test_ticket_text_does_not_steer_route`) xanh, chỉ đổi giá trị stub; `erp_ai/agent/test_runner_status.py` xanh không sửa.
```

### T82 — nguồn: chữ hiện có + "Chèn 8" của `design-w1-fixes-6.md` Điểm 1 + `design-w1-fixes-7.md` Điểm 2 (file `test_classification.py`) + `design-w1-fixes-10.md` Điểm 2 với F-9 (hai file). MƯỜI MỘT file (xem mục 5, L-1)

```
- [ ] T82 — `_reason` lấy tool và cờ khối từ `grant`; bỏ đường cấp cũ và cầu của T76 — files: erp_ai/agent/runner.py, erp_ai/agent/tools/registry.py, erp_ai/agent/prompts.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/tools/test_registry.py, erp_ai/agent/tools/test_site_api.py, erp_ai/tests/test_tasks.py, erp_ai/tests/test_architecture.py, erp_ai/agent/test_classification.py, erp_ai/agent/tools/test_propose_change.py, erp_ai/agent/test_run_status.py — test: erp_ai/agent/test_agent_runner.py — depends: T81, T79, T65
  - Tiêu chí: AC-3, AC-6, AC-7, AC-22, AC-61 (đầu-cuối); `U1.md:263`, `:166` (danh sách xóa), `:227`; gỡ cầu `design-w1-fixes-3.md` Điểm 1. Bảy file vì xóa hàm cũ và gỡ cầu phải cùng commit với mọi nơi gọi và mọi test dựng context bằng `change_enabled`.
  - Chèn 8 (quyết định 07:21 (b) của team-leader, sửa theo `design-w1-fixes-6.md` Điểm 1; file thứ tám của `files:`): T82 thêm `erp_ai/tests/test_architecture.py` vào `files:` và sửa ĐÚNG 15 chỗ E1..E15 của bảng `design-w1-fixes-6.md` Điểm 1, không chỗ nào khác: thêm hằng `RUNNER_SCHEMA_CALL = "schemas"` (giữ `SCHEMA_FUNCTION = "get_tool_schemas"` vì `get_tool_schemas` vẫn là hàm tiêu thụ spec, `U1.md:162`); `SPEC_CONSUMERS` bỏ `"_grants_group"`; luật runner, chữ lỗi, docstring và `assertIn` của `test_registry_has_one_grant_function` so với `RUNNER_SCHEMA_CALL` (hệ quả `design-addendum-1-U1.md:263`); `GRANT_CLEAN` bỏ `_grants_group`, runner giả gọi `granted = grant(inputs)` / `granted.schemas()`; ca sạch `aliased` đổi sang `grant as issue`, thêm ca sạch `chained`; ca đỏ `"second schema call"`, `"other schema function"`, `"no schema call"` đổi chuỗi theo runner giả mới, thêm ca `"runner back on the legacy schema function"`, xóa ca `"_grants_group skips the grant function"`. Đỏ trước: trên mã T82 (registry, runner đã đổi), chưa sửa file này, `cmd.test_one` `erp_ai/tests/test_architecture.py` FAILED ở `test_registry_has_one_grant_function` (`_grants_group missing`, `schema calls`, `assertIn`); sau 15 chỗ → cả file xanh. Reviewer kiểm diff của file chỉ có 15 chỗ này. Chuỗi chủ file: … T80 → T82 → T83 …; T83 vẫn giữ ba luật mới của nó.
  - Chèn 10 (F-9 của `preflight-w1.md:30`; phán `files:` của team-leader, đầu vào tương đương do designer xác nhận ở `design-w1-fixes-10.md` Điểm 2; file thứ mười, thứ mười một của `files:`): chỉ đổi ba lời gọi `get_tool_schemas` chữ ký cũ và dòng import của chúng, không đổi khẳng định nào: `erp_ai/agent/tools/test_propose_change.py:76` → `get_tool_schemas(GrantInputs(effective_level=level, main_path_level=level, has_instructor=has_instructor, switches=PermissionSwitches(record_tools=change_enabled, code_change=change_enabled)))`; `:437` → `get_tool_schemas(GrantInputs(effective_level="L3", main_path_level="L3", has_instructor=True, switches=PermissionSwitches(record_tools=True, code_change=True)))`; `erp_ai/agent/test_run_status.py:45` → `get_tool_schemas(GrantInputs(effective_level=LEVELS[-1], main_path_level=LEVELS[-1], has_instructor=True, switches=PermissionSwitches()))`; `GrantInputs` import từ `erp_ai.agent.tools.registry`, `PermissionSwitches` từ `erp_ai.agent.policy`. Expect thêm: `cmd.test_one` xanh cả file `erp_ai/agent/test_run_status.py` (`erp_ai/agent/tools/test_propose_change.py` đã có ở dòng Expect); reviewer kiểm diff của hai file chỉ có ba lời gọi và dòng import (dòng số đo ở `team/FEAT-007` @ `caa555a`).
  - Receives: `grant`, `Grant` (T76, T77); `build_reason_system` năm cờ và lõi `core_prompt(**cờ)` (T79); `test_registry.py::TestGrantFeat007::test_record_block_hidden_when_unrestricted_granted` (T77) giữ luật "khối toàn quyền thay khối bản ghi".
  - Returns: `_reason` dùng `granted = grant(context.grant_inputs())`; `get_tool_schemas(inputs: GrantInputs) -> list[dict]`; xóa `grants_change_tools`, `grants_site_admin_tools`, `grants_unrestricted_tools`, `_grants_group`, `_legacy_inputs`, hai phép suy `prompts.py:328,330`. Gỡ cầu: `ToolContext.grant_inputs()` lấy (2) chỉ từ `self.record_tools` (đúng `U1.md:166`). Test chỉ đổi đúng các chỗ sau, không đổi khẳng định nào khác: `test_site_api.py` — các dòng gọi hàm đã xóa (`TestSiteApiGrant.names` `:105-107` và `:858-863` dựng `GrantInputs`, công tắc đang thử đặt vào (2) ở `:105` và vào (1) ở `:858`; `test_grants_site_admin_tools_matches_the_grant` đọc `grant(...).record_block`), `_context` (`:91-101`) thêm tham số `record_tools=True` truyền vào `ToolContext`, `test_execute_refuses_when_not_granted` đổi ca `_context(change_enabled=False)` thành `_context(record_tools=False)`; `test_tasks.py` — `_agent_calls` (`:285-294`) thêm `record_tools=True`; `test_agent_runner.py` — thêm `record_tools_enabled=1` vào `set_agent_settings` của `setUp` các lớp `TestRunnerSiteAdminTools`, `TestRunnerRecordSnapshots`, `TestRunnerTurnUndo`, `TestRunnerPrivilegeAlarmEndToEnd`, `TestRunnerChangeGrant`; trong `test_not_offered_with_switch_off_or_below_l3` ca công tắc tắt đổi `{"code_change_enabled": 0}` thành `{"record_tools_enabled": 0}` và dòng đặt lại thêm `record_tools_enabled=1`; test nào khác của file chỉ đỏ vì gỡ cầu thì thêm đúng khóa `record_tools_enabled=1` vào `set_agent_settings` của nó, không sửa khẳng định; `test_classification.py` (`design-w1-fixes-7.md` Điểm 2, file thứ chín) — bốn test `test_reason_system_with_change_tools_adds_approval_block`, `test_reason_system_with_site_admin_tools_adds_record_block`, `test_reason_system_with_unrestricted_tools_adds_full_access_block`, `test_act_now_block_only_with_action_tools` đổi đúng các chỗ của Điểm 2, giữ tên test (dòng số đo ở `team/FEAT-007` @ `10781fc`, dịch theo T80, T81).
  - Expect: `TestRunnerGrant::test_reason_prompt_flags_come_from_grant`, `::test_over_budget_run_offers_l1_tool_set`, `::test_log_seeded_midday_over_budget_next_run_l1`, `::test_low_confidence_with_instructor_and_act_now_keeps_record_tools`; `erp_ai/agent/test_prompts.py::TestCorePrompt::test_no_wait_for_ok_five_switches_off_l1_to_l3`, `::TestReasonSystem::test_each_block_present_iff_its_flag` (đủ 5 khối) xanh. Gỡ cầu đỏ trước: đổi `erp_ai/agent/tools/test_registry.py::TestGrantInputs::test_bridge_change_switch_still_brings_record_tools` thành `::test_record_tools_only_from_its_own_switch` (`change_enabled=True, record_tools=False` → (2) False) → đỏ (`AssertionError: True is not false`), gỡ vế `or self.change_enabled` → xanh. `cmd.test_one` xanh cả file: `erp_ai/agent/tools/test_site_api.py`, `erp_ai/tests/test_tasks.py`, `erp_ai/agent/tools/test_registry.py`, `erp_ai/agent/tools/test_propose_change.py`, `erp_ai/agent/test_agent_runner.py`. `cmd.test_one` xanh cả file `erp_ai/tests/test_architecture.py` (Chèn 8). Chèn 6, CI-6 (`arch-impact-chg-002.md:95`): `test_prompts.py`, `test_agent_runner.py` không chép chữ của `CHANGE_TOOLS_BLOCK` ngoài dòng neo P-1. `erp_ai/agent/test_classification.py` xanh cả file (`cmd.test_one`), bốn test của Điểm 2 đỏ trước trên mã T79.
```

### T83 — nguồn: `design-w1-fixes-9.md` Điểm 2, Điểm 3 (cả khối)

```
- [ ] T83 — Luật kiến trúc của U1 — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T82
  - Tiêu chí: ADR-030 Ràng buộc, QĐ 4; AC-22, AC-61; `U1.md:401`, `:431`, `:440`, `:443`; C-2 (không có `site_environment` trong `POLICY_FIELDS`); F-11, F-12 theo `design-w1-fixes-9.md` Điểm 2, Điểm 3 (định nghĩa "phép so sánh": phần chung).
  - Receives: mã U1 đã merge (T66–T82).
  - Returns: `POLICY_FIELDS` thêm `record_tools_enabled`, `act_now_enabled`, `one_click_approval_enabled`, `level_cap_a`..`level_cap_f`, `confidence_threshold`; luật cho phép `erp_ai_setting.py`; ba luật mới. Hai luật so sánh dùng chung `ORDERING_OPS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)`, `operand_names(node)`, `ordering_compares(tree)`; quét `only_python(sources)` trừ đúng `POLICY_FILE`, không miễn file nào khác; chỉ nút `ast.Compare` có toán tử thứ tự mới tính (gán, gọi hàm, đối số, khóa dict, `is`/`in`/`==`/`!=` không tính). `check_threshold_compared_only_in_policy(sources) -> list`: bắt toán hạng nêu tên khớp `is_confidence_name` (đúng `threshold` hoặc `do_tin_cay_pct`, chứa `confidence_threshold`, tận cùng `confidence_pct`, không phân biệt hoa thường); miễn đúng ca một toán hạng khớp và mọi toán hạng khác là `CONFIDENCE_PCT_MIN`/`CONFIDENCE_PCT_MAX`. `check_no_spent_comparison_outside_policy(sources) -> list`: bắt toán hạng nêu đúng `spent_this_month_usd`, `monthly_budget_usd` hoặc `month_spend_usd`. Thông điệp cả hai: `"<file>:<dòng>: compares <tên> outside agent/policy.py"`. Thân hàm theo `design-w1-fixes-9.md` Điểm 2, Điểm 3. Luật mới bắt được vi phạm trong mã đã merge → trả `DESIGN_CONFLICT` kèm danh sách, không sửa mã nguồn.
  - Expect: `TestArchitecture::test_runner_takes_tools_and_flags_from_grant`, `::test_threshold_compared_only_in_policy`, `::test_no_spent_comparison_outside_policy` xanh. Mỗi luật so sánh có ca đỏ bằng chuỗi mẫu: đỏ trước — thêm `TestScannersCatchViolations::test_threshold_scanner_catches_comparison_outside_policy_and_allows_reads` và `::test_spent_scanner_catches_comparison_outside_policy_and_allows_reads` trước khi có hàm → `NameError: name 'check_threshold_compared_only_in_policy' is not defined` / `NameError: name 'check_no_spent_comparison_outside_policy' is not defined`; viết hàm → xanh. Chuỗi mẫu phải bắt: `"def f(settings, pct):\n\treturn pct < settings.confidence_threshold\n"` ở `agent/runner.py` → `agent/runner.py:2: compares confidence_threshold outside agent/policy.py`; `"def f(settings):\n\treturn settings.spent_this_month_usd > settings.monthly_budget_usd\n"` ở `agent/runner.py` → `agent/runner.py:2: compares spent_this_month_usd outside agent/policy.py`; đủ các ca bắt và cho phép liệt kê ở `design-w1-fixes-9.md` Điểm 2 mục Test, Điểm 3 mục Test (trong đó dòng runner `threshold = policy.confidence_threshold(settings)`, bảng `INT_LIMITS` của controller, `erp_ai_cost.py:130`, `tasks.py:76`, `erp_ai_setting.py:228` là ca cho phép). `cmd.test_one` của `erp_ai/tests/test_architecture.py` xanh cả file.
```

### T85 — nguồn: `design-w1-fixes-10.md` Điểm 3 (thêm dòng "Chèn 10" ngay sau Returns; các dòng khác giữ)

```
- [ ] T85 — Loại dòng `bot_action`, hai trigger mới, môi trường tự điền [migrate] — files: erp_ai/agent/run_log.py, erp_ai/agent/test_run_log.py, erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json, erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py, erp_ai/tests/test_doctype_descriptions.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/test_run_log.py — depends: T84, T70, T83, T64, T173
  - Tiêu chí: AC-10; `U3.md:77-82`, `:120-128`, `:146` vế (a), (c), (d), `:228`; F-5 (hằng và option JSON cùng commit, nên sáu file). Vế (b) của `:146` ở T93.
  - Receives: `policy.site_environment` (T70).
  - Returns: `ENTRY_TYPE_BOT_ACTION`, `ENTRY_TYPES` 5 giá trị, `TRIGGER_SETTING_SAVE`, `TRIGGER_SCHEDULED_JOB`, `BOT_ACTION_TRIGGERS`, `TOOL_PERMISSION_SWITCH`; `write_entry` kiểm dòng `bot_action`, tự điền `site_environment`; option và mô tả của `entry_type`, `trigger`; ba cụm bắt buộc mới. R5-14 (ADR-024 Ràng buộc 5): `write_entry` giữ `insert` và `commit` trong cùng lời gọi; phép kiểm dòng `bot_action` chạy trước `insert`, ném lỗi thì 0 dòng; reviewer dán thân `write_entry` sau sửa vào review.
  - Chèn 10 (`design-w1-fixes-10.md` Điểm 3, trần 400 của `preflight-w1.md:47`): mô tả `trigger` của `erp_ai_log.json` là ĐÚNG chuỗi sau (289 ký tự), thay câu thêm của `U3.md:228` cho trường này; mô tả `entry_type` theo `U3.md:228` (346 ký tự): "Nguồn kích hoạt — ticket_insert: phiếu mới tạo; comment_mention: bình luận có từ khóa kích hoạt; change_action: bước của đề xuất thay đổi; setting_save: người lưu cấu hình đổi công tắc quyền; scheduled_job: việc theo lịch hay theo sự kiện, không qua model. Hệ thống tự ghi, không sửa được." Expect thêm: `erp_ai/tests/test_doctype_descriptions.py::TestDoctypeDescriptions::test_descriptions_at_most_400_chars`, `::test_required_phrases_present`, `::test_read_only_fields_say_system_writes` xanh sau `cmd.migrate`.
  - Expect: `TestWriteEntry::test_every_row_gets_site_environment`, `TestBotAction::test_bot_action_needs_known_trigger_actions_and_zero_cost`; `test_erp_ai_log.py::TestOptions::test_entry_type_and_trigger_options`; `test_architecture.py::test_entry_types_unchanged` (ghim 5), `::test_log_trigger_options_match_run_log`, `::test_policy_does_not_import_run_log`; `test_doctype_descriptions` xanh sau `cmd.migrate`.
```

### T87 — nguồn: `design-w1-fixes-7.md` mục "Chuỗi chủ file" (chỉ `depends:` thêm T79)

```
- [ ] T87 — Lưu cấu hình đổi công tắc quyền ghi một dòng nhật ký — files: erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — depends: T86, T72, T32, T79
  - Tiêu chí: AC-4 (dòng nhật ký), AC-10 (a); `U3.md:205-214`; C-9 (`w1a.md:63`); A-U3-1, A-U3-2, A-U3-8.
  - Receives: `policy.PERMISSION_SWITCH_FIELDS` (T66); `notify_permission_switches` (T6); `write_bot_action` (T86).
  - Returns: `_permission_switch_fields()` trả `policy.PERMISSION_SWITCH_FIELDS`, cả `notify_permission_switches` và hàm mới gọi nó; `record_permission_switch_changes(self) -> str | None` gọi cuối `on_update`. Controller không viết tên công tắc nào (D-7).
  - Expect: `TestPermissionSwitchLog::test_each_switch_on_writes_one_row`, `::test_two_switches_on_one_row_two_entries`, `::test_save_without_switch_change_no_row`, `::test_switch_off_writes_row_without_notice`, `::test_log_failure_fails_the_save`, `::test_switch_set_matches_section_checks` xanh.
```

### T89 — nguồn: F-9 (quyết định 09:10; chỉ `depends:` thêm T82)

```
- [ ] T89 — Comment đề xuất không ký liên kết khi công tắc (5) tắt — files: erp_ai/agent/tools/propose_change.py, erp_ai/agent/tools/test_propose_change.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/tools/test_propose_change.py — depends: T76, T88, T82
  - Tiêu chí: AC-11; `U3.md:192-197`. Test ba liên kết của FEAT-004 T53 đặt `ctx.one_click_approval=True` (NFR-8).
  - Chèn 11 (F-9 của `preflight-w1.md:30`; phán `files:` của team-leader, quyết định 09:10): `depends:` thêm T82 vì T82 nay sửa `erp_ai/agent/tools/test_propose_change.py` (Chèn 10 của T82); chuỗi chủ file đó: T82 → T89 → T105.
  - Receives: `ToolContext.one_click_approval` (T76). Chèn 6, CI-3 (`arch-impact-chg-002.md:92`): nếu T126 đã merge khi T89 sẵn sàng thì viết trên `_comment` mới; test chỉ khẳng định có/không có liên kết ký (`decision_path`) và nhãn `OPEN_PROPOSAL_LABEL`, không khẳng định câu đầu; có ca khối nhiều mục, công tắc (5) tắt → 0 liên kết ký.
  - Returns: `OPEN_PROPOSAL_LABEL = "Mở đề xuất để Duyệt hoặc Từ chối"`; `_comment` chỉ gọi `change_link.decision_path` trong nhánh `one_click_approval`.
  - Expect: `TestOneClickGate::test_switch_off_comment_has_no_decision_links`, `::test_switch_off_never_signs`, `::test_switch_on_comment_matches_feat004_links`; nửa `_comment` của `test_decide_reads_one_click_switch_before_signature` xanh.
```

### T92 — nguồn: F-13 (quyết định 09:10)

```
- [ ] T92 — Mục hành động của bước định tuyến đi qua `action_entry` — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/test_runner_routing.py — test: erp_ai/agent/test_agent_runner.py — depends: T91
  - Tiêu chí: AC-10; `U3.md:166`.
  - Chèn 11 (F-13 của `preflight-w1.md:34`; phán `files:` của team-leader, quyết định 09:10; file thứ ba của `files:`): T92 thêm `erp_ai/agent/test_runner_routing.py` vào `files:`, chỉ sửa một khẳng định so dict bốn khóa của mục định tuyến (`:192-195` ở `team/FEAT-007` @ `aedc360`) thành mục bảy khóa của `action_entry`; lý do trong commit: NFR-8 (như T91 ghi cho `test_agent_runner.py`); `cmd.test_one` xanh cả file `erp_ai/agent/test_runner_routing.py`. Chuỗi chủ file: T72 → (T81, chỉ bản B) → T92 → T108. Sai thì: gỡ file khỏi `files:` và chuyển designer.
  - Receives: `before`/`after` của `route_ticket` (`route_ticket.py:71-72`).
  - Returns: `_route_action(tool, doctype, name, ok, reason=None, rule=None, *, value_before=None, value_after=None, instructor=None)`; không còn dict mục hành động viết tay trong `runner.py`.
  - Expect: `TestActionLog::test_route_entries_use_shared_shape` xanh.
```

### T93 — nguồn: khối của `design-w1-fixes-10.md` Điểm 1 (F-14) + F-15 (quyết định 09:10; file nối sau `erp_ai/tests/test_tasks.py` theo Điểm 1 mục 5)

```
- [ ] T93 — `write_entry` từ chối mục hành động viết tay — files: erp_ai/agent/run_log.py, erp_ai/agent/test_run_log.py, erp_ai/tests/test_architecture.py, erp_ai/tests/test_tasks.py, erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py — test: erp_ai/agent/test_run_log.py — depends: T92, T89, T82
  - Tiêu chí: AC-10; `U3.md:146` vế (b), `:368`; ADR-033 Ràng buộc; F-14 (`design-w1-fixes-10.md` Điểm 1: `test_tasks.py` dựng mục năm khóa và ghi `actions` hỏng qua `write_entry`, nên đổi cùng task; chuỗi chủ `test_tasks.py`: T94 → T82 → T93).
  - Chèn 11 (F-15 của `preflight-w1.md:36`; phán `files:` của team-leader, quyết định 09:10; file thứ năm của `files:`): T93 thêm `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py` vào `files:`, chỉ sửa `_actions_just_over_small_text` (`:149-155` ở `team/FEAT-007` @ `aedc360`) và hai chỗ dùng nó (`:167-172`) để dựng mục bằng `run_log.action_entry`; không đổi khẳng định nào; `cmd.test_one` xanh cả file `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py`. Chuỗi chủ file: T85 → T93. Sai thì: gỡ file khỏi `files:` và chuyển designer.
  - Receives: mọi nơi dựng mục đã qua `action_entry` (T91, T92).
  - Returns: `write_entry` ném `ValueError`, 0 dòng, khi một phần tử `actions` thiếu khóa của `ACTION_KEYS`; luật `test_action_entries_built_only_in_run_log`. Luật bắt được vi phạm ở mã đã merge → trả `DESIGN_CONFLICT` kèm danh sách. R5-14: phép kiểm `ACTION_KEYS` chạy trước `insert`; `insert` và `commit` vẫn trong cùng lời gọi `write_entry`; reviewer dán thân `write_entry` sau merge, `erp_ai/agent/test_agent_runner.py` (gồm test ADR-024 QĐ 2 của FEAT-005) chạy lại xanh. T93 đứng trước T110 (R5-15). Test chỉ đổi đúng các chỗ sau trong `erp_ai/tests/test_tasks.py`, không đổi khẳng định nào: (1) thân `_hand_action` (`:71-73`) thành `return run_log.action_entry(tool, doctype, name, ok, instructor=INSTRUCTOR)`, chữ ký giữ, khoảng 40 chỗ gọi không sửa; (2) thêm `TestCheckPrivilegeEscalation._bad_actions_row(self, actions_text, at=SEEDED_AT)` ngay sau `_log_row`: `frappe.get_doc({doctype: LOG_DOCTYPE, run_id: "ERPAI-TEST-run", entry_type: "reason", trigger: TRIGGER_TICKET_INSERT, turn: 1, instructor: INSTRUCTOR, actions: actions_text}).db_insert()` (như `erp_ai/agent/test_kpi.py:129-140`), rồi lùi `creation` như `_log_row` `:279`, trả tên dòng; (3) `:1057` và `:1130-1133` đổi `self._log_row(` thành `self._bad_actions_row(`, tham số giữ (dòng số đo ở `team/FEAT-007` @ `caa555a`, dịch theo T82).
  - Expect: `TestWriteEntry::test_hand_built_entry_rejected`; `test_architecture.py::test_action_entries_built_only_in_run_log` xanh. Sửa test (1)–(3) là commit riêng trước commit mã, xanh trên BASE; sau commit mã `cmd.test_one` xanh cả file `erp_ai/tests/test_tasks.py`, trong đó `TestCheckPrivilegeEscalation::test_unusable_snapshot_shapes_listed_without_before_after` (3 subtest `actions`) và `::test_broken_snapshot_json_listed_without_before_after` xanh, khẳng định không đổi; reviewer kiểm diff của `test_tasks.py` chỉ có ba chỗ trên.
```

### T140 — nguồn: `design-w1-fixes-10.md` Điểm 3 (thêm dòng "Chèn 10" ngay sau Returns; các dòng khác giữ)

```
- [ ] T140 — Hai trigger mới `requester_reply`, `kb_draft` trong một commit [migrate] — files: erp_ai/constants.py, erp_ai/agent/queue.py, erp_ai/agent/run_log.py, erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json, erp_ai/agent/policy.py, erp_ai/tests/test_architecture.py, erp_ai/tests/test_doctype_descriptions.py, erp_ai/agent/test_policy.py, erp_ai/agent/test_run_log.py — test: erp_ai/agent/test_policy.py — depends: T130, T93, T75, T125, T139
  - Tiêu chí: AC-41, AC-45, NFR-2; `U6b-fixes.md` Sửa 3, Sửa 4 (`:133-162`); w1a phán quyết (2) (`w1a.md:70-74`). 9 file trong một commit là đòi hỏi của thiết kế (`U6b-fixes.md:141`): commit thiếu một phần thì luật tập hợp đỏ. Không cùng lượt với T43, T49 (chung `test_doctype_descriptions.py`).
  - Receives: `policy.RUN_LIMIT_TRIGGERS` và bộ lọc của `runs_today` (T71); thiếu → `DESIGN_CONFLICT`. `run_log.TRIGGERS`, `BOT_ACTION_TRIGGERS` (T85); `DOCTYPE_CONFIG["ERP AI Log"]["phrases"]`.
  - Returns: `erp_ai/constants.py`: `TRIGGER_REQUESTER_REPLY = "requester_reply"`, `TRIGGER_KB_DRAFT = "kb_draft"` (file giữ 0 dòng import); `queue.VALID_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_REQUESTER_REPLY, TRIGGER_KB_DRAFT)`; `run_log.TRIGGERS` thêm hai hằng đó; option và mô tả `trigger` của `erp_ai_log.json` (`U6b.md:314`), hai cụm `"requester_reply"`, `"kb_draft"` trong `phrases`; `policy.RUN_LIMIT_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_REQUESTER_REPLY)`, không có `TRIGGER_KB_DRAFT`, đúng một chỗ sửa trong `policy.py`.
  - Chèn 10 (`design-w1-fixes-10.md` Điểm 3): mô tả `trigger` của `erp_ai_log.json` là ĐÚNG chuỗi sau (388 ký tự; chuỗi của T85 chèn thêm đoạn `requester_reply: …; kb_draft: …; ` ngay trước `change_action:`, không đổi chữ nào khác), thay câu thêm của `U6b.md:314`: "Nguồn kích hoạt — ticket_insert: phiếu mới tạo; comment_mention: bình luận có từ khóa kích hoạt; requester_reply: người tạo phiếu trả lời tin của bot; kb_draft: soạn bài CSKT nháp khi đóng phiếu; change_action: bước của đề xuất thay đổi; setting_save: người lưu cấu hình đổi công tắc quyền; scheduled_job: việc theo lịch hay theo sự kiện, không qua model. Hệ thống tự ghi, không sửa được." Expect thêm: `erp_ai/tests/test_doctype_descriptions.py::TestDoctypeDescriptions::test_descriptions_at_most_400_chars`, `::test_required_phrases_present` xanh sau `cmd.migrate`.
  - Expect: `test_policy.py::TestRunsToday::test_kb_draft_reason_row_not_counted`, `::test_requester_reply_reason_row_counted` (tăng đúng 1; hai lượt cùng `run_id` → vẫn 1; một dòng `skip superseded` → +0) đỏ trước rồi xanh; `test_architecture.py::test_run_limit_triggers_subset_of_log_triggers` đổi luật thành `set(run_log.TRIGGERS) - set(policy.RUN_LIMIT_TRIGGERS) == {TRIGGER_KB_DRAFT}` (lý do sửa test ghi ở commit: AC-41, AC-45 thêm trigger); `test_run_log.py::TestTriggers::test_triggers_match_queue_and_json`, `test_architecture.py::test_log_trigger_options_match_run_log`, `test_doctype_descriptions` xanh sau `cmd.migrate`.
```

---

## 4. Chuỗi chủ file và `depends:` đổi

### `depends:` đổi (bốn dòng; không dòng nào khác đổi)

| Task | Cũ | Mới | Nguồn |
|---|---|---|---|
| T74 | `T73, T71, T67` | `T73, T71, T67, T72` | F-1 (quyết định 09:10) |
| T87 | `T86, T72, T32` | `T86, T72, T32, T79` | `design-w1-fixes-7.md` mục "Chuỗi chủ file" |
| T89 | `T76, T88` | `T76, T88, T82` | F-9 (quyết định 09:10) |
| T93 | `T92, T89` | `T92, T89, T82` | `design-w1-fixes-10.md` Điểm 1 mục 4 |

Hệ quả điều phối: T74 (đầu làn `runner.py`) nay chờ T72; T89 nay chờ T82, tức sau gần hết U1 (trước đây chỉ chờ T76, T88).

### Hàng "Một file, một chủ" thay cho `plan-w1.md` (và hàng trùng của `plan-w1b.md`)

| File | Chuỗi task (mới) | Thay hàng |
|---|---|---|
| `erp_ai/agent/test_agent_runner.py` | T56 → T72 → T74 → T80 → T81 → T82 → T91 → T92 → T108 → T110 → T111 → T115 → T116 → T117 → T113 → T118 | `plan-w1.md:117` (thêm T74) |
| `erp_ai/agent/test_runner_routing.py` | T72 → (T81, chỉ khi dùng bản B) → T92 → T108 → T109 → T112 → T115 | `plan-w1.md:118` |
| `erp_ai/tests/test_architecture.py` | T122 → T56 → T70 → T71 → T74 → T80 → T82 → T83 → T85 → T88 → T89 → T93 → T99 → T105 → T119 | `plan-w1.md:119` (thêm T82, có từ Chèn 8) |
| `erp_ai/agent/classification.py`, `erp_ai/eval/test_run_eval.py` | T72 | `plan-w1.md:139` (tách) |
| `erp_ai/agent/test_classification.py` | T72 → T79 → T82; T126 đứng ở bất kỳ chỗ nào nhưng không cùng lượt với ba task này | `plan-w1.md:139`, `plan-w1b.md:130` |
| `erp_ai_setting.py`, `test_erp_ai_setting.py` | chuỗi U0 → T56 → T63 → T64 → T72 → T79 → T87 → T124 (T124 còn chờ T53); T32 còn mở (`depends: T20, T29, T56`; T87 chờ T32): không cùng lượt với T72, T79 | `plan-w1.md:124`, `plan-w1b.md:131` |
| `erp_ai_setting.json` | T64 → T125 → T72 → T79 | `plan-w1.md:124`, `plan-w1b.md:131` |
| `erp_ai/agent/tools/propose_change.py` | T89 → T105 (T126 theo `plan-w1b.md:129`) | `plan-w1.md:133` (tách) |
| `erp_ai/agent/tools/test_propose_change.py` | T82 → T89 (trước hoặc sau T126) → T126 → T105; T126 không cùng lượt với T82 | `plan-w1.md:133`, `plan-w1b.md:129` |
| `erp_ai/tasks.py` | T94 | `plan-w1.md:136` (tách) |
| `erp_ai/tests/test_tasks.py` | T94 → T82 → T93 | `plan-w1.md:136` |
| `erp_ai_log.json` | T85 (→ T140, `plan-w1b.md:115`) | `plan-w1.md:141` (tách) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py` | T85 → T93 | `plan-w1.md:141` |
| `erp_ai/agent/changes/test_result_comment.py` | T80 | hàng mới |
| `erp_ai/tests/test_ticket_panel.py` | T175 → T75 (bản a) hoặc T175 → T80 (bản b) | hàng mới |
| `erp_ai/agent/test_run_status.py` | T82 | hàng mới |

Không đổi: `runner.py`, `prompts.py`/`test_prompts.py`, `registry.py`/`test_registry.py`, `authority.py`/`test_authority.py`, `site_api.py`/`test_site_api.py`, `run_log.py`/`test_run_log.py`, `test_doctype_descriptions.py`, `missed_scan.py`, `redact.py`.

Task `[migrate]` của đợt 1a thêm T79 (và T72, đã có nhãn): danh sách ở `plan-w1.md:143` thành T64, T72, T79, T85.

---

## 5. Mâu thuẫn

Mâu thuẫn về QUYẾT ĐỊNH giữa hai phán quyết: 0. Không phán quyết nào bảo bỏ thứ mà phán quyết khác bảo thêm.

Có năm chỗ CHỮ lệch nhau, vì bốn lượt designer chạy song song và không thấy bài của nhau. Khối ở mục 3 ghép theo phép hợp (mỗi phán quyết giữ đủ phần của nó); hai văn bản gốc chép dưới đây để team-leader soát. Team-leader coi chỗ nào là mâu thuẫn thật → không dán khối của task đó và phán lại.

- **L-1, T82, dòng tiêu đề và số file.** `design-w1-fixes-7.md:58` ("thay cả dòng"): `… erp_ai/tests/test_tasks.py, erp_ai/tests/test_architecture.py, erp_ai/agent/test_classification.py — test: …` (chín file, gọi `test_classification.py` là "file thứ chín"). `design-w1-fixes-10.md:83` ("dán thay dòng tiêu đề"): `… erp_ai/tests/test_tasks.py, erp_ai/tests/test_architecture.py, erp_ai/agent/tools/test_propose_change.py, erp_ai/agent/test_run_status.py — test: …` (mười file, không có `test_classification.py`; "Chèn 10" gọi hai file của nó là "file thứ chín, thứ mười"). Journal 09:18 ghi "T82 thành 10 file". Khối ghép: MƯỜI MỘT file; trong "Chèn 10" chữ "thứ chín, thứ mười" đổi thành "thứ mười, thứ mười một"; chữ "file thứ chín" của `design-w1-fixes-7.md` giữ. Câu "Bảy file vì …" ở Tiêu chí của T82 là chữ cũ, không nguồn nào bảo sửa, để nguyên.
- **L-2, T80, dòng tiêu đề.** `design-w1-fixes-8.md:112` ("thay cả khối"): năm file, và Điểm 1 mục 3 viết "Không thêm file vào `files:` của T80". `design-w1-fixes-9.md:35`: sáu file (thêm `erp_ai/agent/changes/test_result_comment.py`), kèm câu "phán quyết của F-4, F-5, F-6 (người phán khác) chèn thêm vào cùng dòng khi có". `design-w1-fixes-8.md:144` tự ghi không phán `latest_instructor`. Khối ghép: sáu file (bản a), bảy file (bản b với F-4).
- **L-3, chuỗi `test_agent_runner.py`.** F-1 (quyết định 09:10): "chuỗi chủ file T67 → T72 → T74 → T80 …". `design-w1-fixes-8.md:90`: "T67 → T72 → T80 → T81 → T82 → … → T108. (Ghi chú: T74 không có file này trong `files:`…)". Câu của designer tả trạng thái trước F-1. Mục 4 ghép: … T72 → T74 → T80 ….
- **L-4, chuỗi `test_runner_routing.py`.** `design-w1-fixes-8.md:91`, `:133`: "bản A: T72 → T108 → T109 → …; bản B: T72 → T81 → T108". F-13 (quyết định 09:10) thêm file vào T92. Mục 4 và khối T81 bản B ghép: T72 → (T81) → T92 → T108.
- **L-5, số chỗ vá `latest_instructor` trong `test_agent_runner.py`.** `preflight-w1.md:56`: 20 chỗ; `design-w1-fixes-9.md:16`: 24 chỗ (đếm ở `caa555a`). Dòng task viết "mọi", không ghi số; không ảnh hưởng khối.

Ghi chú của quyết định 09:10 (c) và F-4: ghi chú (2) của `preflight-w1.md:45` ("`test_ticket_panel.py:732` … vô hại ở T75, thành F-4 ở T80") nay đã thành việc của T75 (bản a) theo F-4; lời giao T75 chỉ còn cần ghi chú (1).

---

## 6. Kiểm (đã chạy, dán kết quả)

Cách kiểm: đọc 174 dòng tiêu đề task của `tasks.md` (chỉ đọc, `python3 -I -c`, không ghi file), áp các thay đổi `files:` và `depends:` của mục 3 và mục 4 lên bản trong bộ nhớ, rồi tính: ID lạ trong `depends:`; vòng phụ thuộc; với mỗi file, mọi cặp task còn mở cùng có file đó mà không task nào là tổ tiên (theo `depends:`) của task kia. "main" = F-4 ở T75, T81 bản A; "alt" = F-4 ở T80, T81 bản B. Phần `depends:` chỉ lấy tới dấu ` — ` đầu tiên (dòng T35 có ghi chú dài sau `depends: T1`).

```
09:22:34
headers 174 ticked 67
BEFORE: unknown [] cycles [] unordered pairs 53
AFTER main : unknown [] cycles [] unordered pairs 59
  new unordered: [('erp_ai_setting.py', 'T32', 'T79'), ('test_agent_runner.py', 'T74', 'T126'), ('test_classification.py', 'T79', 'T126'), ('test_classification.py', 'T82', 'T126'), ('test_erp_ai_setting.py', 'T32', 'T79'), ('test_propose_change.py', 'T82', 'T126')]
  no longer unordered: []
  new unordered without T126/T32: []
   T72 before T74 : True
   T79 before T87 : True
   T82 before T89 : True
   T82 before T93 : True
   T85 before T93 : True
   T81 before T92 : True
   T175 before T75 : True
   T126 ancestors: [] | T126 in ancestors of T78/T79/T82: [False, False, False]
AFTER alt : unknown [] cycles [] unordered pairs 59
  new unordered: [('erp_ai_setting.py', 'T32', 'T79'), ('test_agent_runner.py', 'T74', 'T126'), ('test_classification.py', 'T79', 'T126'), ('test_classification.py', 'T82', 'T126'), ('test_erp_ai_setting.py', 'T32', 'T79'), ('test_propose_change.py', 'T82', 'T126')]
  no longer unordered: []
  new unordered without T126/T32: []
   (bảy dòng "before" và dòng T126 giống hệt "main")
```

Chuỗi theo `depends:` của các file đổi chủ, sau khi áp (rút gọn từ đầu ra của cùng phép kiểm, không phải chép nguyên văn: bỏ đuôi chuỗi sau T118 và gom các cặp có T126 thành chữ "T126 trôi"; bản "main"; "done" = task đã tick có file đó):

```
agent/test_agent_runner.py | done: T56,T59,T67 | open: T72 → T74 → T80 → T81 → T82 → T91 → T92 → T108 → T110 → T111 → T115 → T116 → T113 → T117 → T118 → … (T126 trôi)
agent/test_classification.py | done: T27,T62 | open: T72 → T79 → T82 (T126 trôi)
erp_ai_setting.json | open: T72 → T79 | unordered: []
erp_ai_setting.py, test_erp_ai_setting.py | open: T32 → T72 → T79 → T87 → T124 | unordered: (T32,T72) có từ trước, (T32,T79) mới
agent/changes/test_result_comment.py | open: T80 | unordered: []
tests/test_ticket_panel.py | done: T175 | open: T75 (alt: T80) | unordered: []
agent/test_runner_routing.py | done: T59 | open: T72 → T92 → T108 → T109 → T112 → T115 (alt: T72 → T81 → T92 → …) | unordered: []
agent/tools/test_propose_change.py | open: T82 → T89 → T105 (T126 trôi)
agent/test_run_status.py | open: T82 | unordered: []
tests/test_tasks.py | done: T94 | open: T82 → T93 | unordered: []
erp_ai_log/test_erp_ai_log.py | done: T4,T5 | open: T85 → T93 | unordered: []
files per task (main): T74 5, T75 6, T79 6, T80 6, T81 2, T82 11, T92 3, T93 5 (alt: T75 5, T80 7, T81 3)
```

Kết luận từng điểm:

1. **Không ID task lạ:** đúng (`unknown []`), trước và sau.
2. **Không vòng phụ thuộc:** đúng (`cycles []`), trước và sau, cả hai biến thể.
3. **Mỗi file một chuỗi có thứ tự:** đúng cho mọi file đổi chủ, với hai ngoại lệ không do `depends:` mang, phải giữ bằng bảng mục 4:
   - T126 (`depends: —`, trôi theo thiết kế của `plan-w1b.md:102`): bốn cặp mới với T74, T79, T82 trên `test_agent_runner.py`, `test_classification.py`, `test_propose_change.py`.
   - T32 trên `erp_ai_setting.py`, `test_erp_ai_setting.py`: cặp (T32, T72) có từ trước lượt này; cặp (T32, T79) là mới, cùng nguyên nhân (T32 còn mở, không task nào trong T72, T79 chờ nó; T87 chờ cả hai). Lượt gom không thêm `depends:` nào ngoài bốn dòng của mục 4; team-leader muốn `depends:` mang thứ tự này thì phán thêm.
   - Ngoài hai nhóm đó: không cặp chưa xếp thứ tự mới nào (`new unordered without T126/T32: []`).
4. **"T126 không cùng đợt với T78, T79, T82":** KHÔNG do `depends:` bảo đảm (T126 không có tổ tiên, không là tổ tiên của ba task đó). Điều giữ được nó là luật "hai task chung file không chạy song song": sau khi áp, T126 chung với T78 hai file (`prompts.py`, `test_prompts.py`), với T79 ba file (thêm `test_classification.py`), với T82 sáu file (`prompts.py`, `test_agent_runner.py`, `test_classification.py`, `test_propose_change.py`, `test_registry.py`, `test_architecture.py`). Tech-lead build phải kiểm bảng cặp chung file ở preflight mỗi vòng và ghi ràng buộc này vào lời giao; kiểm lúc 09:22: không task nào trong bốn task có nhánh mở (`git branch --list 'team/FEAT-007*'` chỉ có `team/FEAT-007`, `-task-174`, `-task-33`, `-task-76`).

Chưa kiểm được trong lượt này: mọi số dòng trong các khối (`:177`, `:732`, `:192-195`, `:149-155` …) là số của nguồn ở `aedc360`/`caa555a`, lượt gom không mở lại từng file mã để đối chiếu, trừ `test_agent_runner.py:177` (đã thấy `patch.object(runner, "AGENT_USER", …)` ở `caa555a`). Không test nào được chạy (lời giao cấm `bench`).

---

## 7. Ghi chú cho lời giao dev (không thuộc dòng task)

- T75 (`preflight-w1.md:45`, quyết định 09:10 (c)): `_run` phải giữ `comment_name=None` mặc định, vì `test_runner_status.py:817` gọi `runner._run(ticket, "comment_mention")` hai tham số.
- T80 (`preflight-w1.md:56-57`): đã vào dòng task qua `design-w1-fixes-9.md` Điểm 1 (mọi chỗ gọi `latest_instructor`) và `design-w1-fixes-8.md` Điểm 1 (bản vá ở `RunnerTestBase`, không sửa từng test `comment_mention`).
- T74, T75, T92, T93 (bốn phán quyết `files:`): lần gọi dev đầu chạy module nêu ở dòng "Chèn 11" trước khi sửa mã để xác nhận test đỏ đúng chỗ preflight nêu (`preflight-w1.md:63`: chưa phát hiện nào được chạy thử).
- T79: `"modified"` của `erp_ai_setting.json` tăng 1 giờ so với mốc trên nhánh lúc dev bắt đầu (`design-w1-fixes-7.md` Điểm 3 mục 4).
- T174: reviewer vòng 2 so mã của dev với mục "Mã đề xuất" và đầu ra RED với "9 subtest" (`design-w1-fixes-5.md:226`).
- Mọi lời giao: T126 không cùng đợt với T78, T79, T82 (quyết định 09:18 (b)).
- Cho As-Built và báo người, không chặn (quyết định 09:18 (d)): hai luật kiến trúc của T83 không lần theo dữ liệu; ở L0 hàm cấp mới không trả tool nào; mô tả `trigger` bỏ vế "(thường do người duyệt thực hiện)".
