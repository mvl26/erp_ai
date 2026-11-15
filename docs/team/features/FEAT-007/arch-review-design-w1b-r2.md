Feature: FEAT-007
Stage: architect
Author-agent: architect
Date: 2026-11-14
Approved-by:
<!-- G2b không áp dụng (team.py: chỉ cổng G5). Bản rà soát vòng 2, không có cổng. -->

# Rà soát kiến trúc vòng 2: hai bản sửa design đợt 1 (U4b + U8, U6b)

REVIEW: ok (U4b + U8 duyệt; U6b duyệt kèm 3 điều kiện E-1..E-3 mà tech-lead chép nguyên văn vào task)
Bản sửa U4b + U8 giải xong W-1..W-3 và các phán quyết (1), (2), (4), không phá thêm ADR-005, ADR-006, ADR-030 hay ADR-033. Bản sửa U6b giải xong X-1..X-3 và các phán quyết (1b), (3a)–(3d). Tuy vậy, ở ba chỗ U6b vẫn trái quyết định (i) của team-leader và hợp đồng R4 của U4b: tính "lần hỏi", bảng `NOTICE_TRIGGERS`, và thứ tự task `reply.py`. Cả ba sửa được ở mức hành vi ngay trong file này (mục 4), nên không cần thêm vòng designer (theo cách của `arch-review-design-w1a.md`).

## Căn cứ (đọc trực tiếp, 2026-11-14, `develop` @ `431bf55`; đích đã biết nên không gọi Explore)

- Đã đọc hết `design-addendum-1-U4b-U8-fixes.md` (500 dòng) và `design-addendum-1-U6b-fixes.md` (407 dòng); `arch-review-design-w1b.md`; `arch-review-design-w1a.md`; `journal/FEAT-007.md:12-17`; `journal-part3.md:25-26`.
- `erp_ai/agent/policy.py:80-92`: `runs_today` lọc `entry_type in (classify, reason)`, chưa lọc trigger.
- `erp_ai/agent/run_log.py:10`, `:45`: `CHANGE_TRIGGERS = (TRIGGER_CHANGE_ACTION,)` là một nhánh riêng của `TRIGGERS`. `changes/transitions.py:123` là chỗ duy nhất dùng `trigger=TRIGGER_CHANGE_ACTION`. Vậy bộ lọc `RUN_LIMIT_TRIGGERS` của U1 không làm đổi gì hôm nay, đúng như `arch-review-design-w1a.md` (2) đã nói.
- `erp_ai/agent/queue.py:1-3` chỉ import `frappe` và `erp_ai.constants`. `runner.py:1-45` hiện không import `queue`. Cạnh mới `runner → queue` mà U6b Sửa 1 thêm vì thế không tạo vòng.
- `ADR-033.md:28` (QĐ 4: trigger "người tạo trả lời" được đếm, "soạn CSKT" không đếm) và `:59` (Ràng buộc: tập trigger được đếm định nghĩa một lần).
- T22a chưa có trong `tasks.md`. Việc chèn đang chờ (`journal-part3.md:26`, `journal/FEAT-007.md:12`).
- STD-short đã đọc lại, trích: "STD-DESIGN-4 (2) Reuse existing logic instead of duplicating it."

## 1. Kết luận theo file sửa

| File | Kết luận | Lý do |
|---|---|---|
| `design-addendum-1-U4b-U8-fixes.md` | **approve** | 3/3 major đã giải và mỗi major có test riêng. Phán quyết (1), (2), (4), C-5 và mục 5 đã vào đúng chỗ. Hợp đồng R4 (`:469-477`) khớp với các quyết định (i)–(iii). Chỉ còn 2 minor (mục 5). |
| `design-addendum-1-U6b-fixes.md` | **approve kèm E-1..E-3** | 3/3 major đã giải. Còn 3 chỗ lệch với bản sửa U4b và với quyết định (i): Sửa 9 ý 3 (`:219`), Sửa 10 (`:225-231`), thứ tự task file mới (`:217`). Điều kiện E-1..E-3 thắng các dòng đó. Không phải design-defect: khung Cửa vào → Lõi → Cổng model giữ nguyên, không cần ADR mới. |

## 2. Từng finding và phán quyết gốc

| Finding / phán quyết | Nguồn | Trạng thái | Dòng của file sửa |
|---|---|---|---|
| W-1 `ai_created_labels` permlevel 0, ghi ở `before_insert` | w1b mục 2 | **đã giải** | U4b-fixes `:36-77` (Fix 1). Ghi ở `validate` khi `is_new()`, tức sau `validate_higher_perm_levels`. Bản cũ giữ cố định ở mọi phiên. Thêm 4 test `:374-379`. |
| W-2 hai nguồn độ tin cậy | w1b mục 2 | **đã giải** | U4b-fixes `:81-102` (Fix 2) và `:138-160` (Fix 5). Chỉ còn một đường ghi là `apply_route`. AST ghim chỗ gán (`:160`). |
| W-3 tool tính lại mức đường chính | w1b mục 2 | **đã giải** | U4b-fixes `:106-114` (Fix 3). Tool đọc `ctx.grant_inputs().main_path_level`. AST: 0 lời gọi hàm tính mức trong `tools/*.py`. Còn minor m-1. |
| X-1 khóa "người tạo trả lời" không theo tên Communication | w1b mục 3 | **đã giải** | U6b-fixes `:41-107` (Sửa 1). `job_id` và `run_id` = khóa có tên Communication (ADR-033 QĐ 2, 6). (r1) dừng mà không ghi gì. Có test ca `STARTED` (`:100`) và ca tin đến giữa lần chạy (`:104`). |
| X-2 `runs_today` không đơn vị nào lọc trigger | w1b mục 3 | **đã giải** | U6b-fixes `:133-152` (Sửa 3). Chủ là U1 theo C-3 của w1a. U6b chỉ nối `requester_reply`. Điều kiện bắt đầu `:142`. |
| X-3 thiếu 2 test ADR-033 cho đóng F im lặng | w1b mục 3 | **đã giải** | U6b-fixes `:111-129` (Sửa 2). Có hai test `:125-126`. Rollback về savepoint theo từng phiếu. Rủi ro gửi email hai lần còn lại: m-3. |
| Minor U4b (a)–(e) | w1b mục 2 | đã giải | U4b-fixes `:260-270` (Fix 11). |
| Minor U6b (a)–(f) | w1b mục 3 | đã giải | Sửa 15 `:282-288`, Sửa 12 `:249-260`, Sửa 13 `:264-270`, Sửa 14 `:274-278`, Sửa 6 `:176-186`, Sửa 9 `:212-218`. |
| (1) `ai_created_labels` ở T22a | w1b mục 4 | đã giải | U4b-fixes `:118-134` (Fix 4), thời điểm ghi ở Fix 1. Phụ thuộc T22a được chèn (m-4). |
| (1b) quyền HD Article cho Instructor | w1b mục 4 | đã giải | U6b-fixes `:200-208` (Sửa 8). Xem quyết định (ii). |
| (2) `ai_confidence_pct` ở `route_ticket.py` | w1b mục 4 | đã giải | U4b-fixes `:138-160` (Fix 5). |
| (3a) `run_log.py`, `erp_ai_log.json` | w1b mục 4 | đã giải | U6b-fixes `:156-162` (Sửa 4). |
| (3b) `test_architecture.py`, 6 đích | w1b mục 4 | đã giải | U6b-fixes `:166-172` (Sửa 5). |
| (3c) `tools/read.py` | w1b mục 4 | đã giải | U6b-fixes `:176-186` (Sửa 6). Lọc nằm trong truy vấn, trước `limit` (ADR-034 Ràng buộc 1–2). |
| (3d) `daily_report.py` | w1b mục 4 | đã giải | U6b-fixes `:190-196` (Sửa 7). |
| (3e) chủ `RUN_LIMIT_TRIGGERS` | w1b mục 4 | **thay** bằng quyết định (iii) | U6b-fixes `:138-140`. |
| (4) phần runner của AC-19/25/27/28 | w1b mục 4 | đã giải | U4b-fixes `:164-176` (Fix 6). |
| Mục 5 `prompts.py`: thứ tự, gợi ý C khi `kb_draft` | w1b mục 5 | đã giải, hai file khớp | U4b-fixes `:180-190` (Fix 7) và U6b-fixes `:217-218` (Sửa 9). |
| Mục 5 `runner.py`: thông báo ở `kb_draft` | w1b mục 5 | **hai file lệch** → E-2 | U4b-fixes `:194-226` (Fix 8) và U6b-fixes `:219`. |
| Mục 5 `write_ticket.py`: hai câu hỏi | w1b mục 5 | **hai file lệch** → quyết định (i), E-1 | U4b-fixes `:230-248` (Fix 9) và U6b-fixes `:225-231` (Sửa 10). |
| Mục 5 `handlers.py`, `registry.py` | w1b mục 5 | đã giải, hai file khớp | U4b-fixes `:252-256` và U6b-fixes `:335`, `:334`. |
| w1a C-5 hình dạng `_classify` | w1a mục 3 | đã giải | U4b-fixes `:274-286` (Fix 12). |
| w1a (2) trigger ở `constants.py`, luật tập hợp | w1a mục 4 | đã giải | U6b-fixes `:139`, `:151`. |
| w1a (3) U6b sửa `install.py` | w1a mục 4 | **thay** bằng quyết định (ii) | U6b-fixes `:205`, `:315`. |
| w1a N-2 U6b phụ thuộc U2 | w1a mục 2 | đã giải | U6b-fixes `:182`, `:341`. |

## 3. Các tên dùng chung giữa hai file

| Tên | U4b + U8 | U6b | Khớp? |
|---|---|---|---|
| `mark_asked`, `asked_in_run` | `reply.py` gọi `mark_asked` khi gửi câu hỏi thành công và kiểm `asked_in_run` trước khi gửi (`:242`, `:246`, `:473`, A-U4b-12 `:461`) | `reply.py` không gọi; câu hỏi qua email không tính (`:227-231`, A-U6b-10 `:374`) | **Không** → E-1 |
| `NOTICE_TRIGGERS` | danh sách cho phép ở `runner.py`, 3 khóa; U6b thêm `TRIGGER_REQUESTER_REPLY` vào ô cần, không bao giờ thêm `TRIGGER_KB_DRAFT` (`:202-207`, `:222`, `:474`) | một điều kiện cấm `trigger == TRIGGER_KB_DRAFT` trong `_notice`; `requester_reply` nhận "cả bốn thông báo" (`:219`, `:331`) nhưng không thêm gì vào bảng | **Không** → E-2 |
| Trigger ở `erp_ai/constants.py` | `CATEGORY_HINT_TRIGGERS` import từ `constants`; test dùng `TRIGGER_KB_DRAFT`, `TRIGGER_REQUESTER_REPLY` vì task `prompts.py` của U8 cắt sau U6b (`:186`, `:190`); U4b không sửa `constants.py` (`:313`) | `TRIGGER_REQUESTER_REPLY`, `TRIGGER_KB_DRAFT` ở `constants.py`, cùng commit trigger (`:139-141`) | Có |
| Thứ tự `prompts.py` | U1 → U4b → U6b → U8 (`:188`, `:317`) | U1 → U4b → U6b → U8 (`:217`, `:332`) | Có |
| Thứ tự `runner.py` | U1 → U2 → U3 → U4b → U6b (`:328`, `:343`) | U1 → U2 → U3 → U4b → U6b (`:217`, `:331`) | Có |
| Task file mới của U6b chạy song song với U4b | — (R4 coi `reply.py` là đơn vị gọi `mark_asked`) | `reply.py` chạy song song được (`:217`) | **Không** khi theo (i) → E-3 |

## 4. Finding mới và điều kiện cho plan (thắng U6b-fixes ở các dòng nêu)

`severity | STD | file:line | mô tả | sửa`

- **E-1** `major | STD-DESIGN-2 | design-addendum-1-U6b-fixes.md:225-231, :303, :357, :374 | Sửa 10 và A-U6b-10 nói reply.py không đánh dấu lần hỏi. Điều này trái quyết định (i) (journal/FEAT-007.md:16) và hợp đồng R4 của U4b (U4b-fixes :473). Test test_below_threshold_email_question_still_one_ask_comment đòi 1 Communication cộng 1 ask_fallback, trong khi test_marked_run_no_fallback của U4b đòi 0 ask_fallback khi cờ đã đặt. Theo (i), hai test này không cùng xanh được. | Thay Sửa 10 bằng: reply_to_requester(kind="question") kiểm write_ticket.asked_in_run(ctx.run_id) trước khi gửi; đã đặt thì từ chối với REASON_ONE_ASK (import hằng từ write_ticket), 0 Communication; gửi thành công thì gọi write_ticket.mark_asked(ctx.run_id). Không file nào khác đọc hay ghi frappe.flags.erp_ai_asked_runs. Thay test bằng TestKnowledgeActions::test_below_threshold_email_question_is_the_one_ask: 69/70, model stub chỉ gọi reply_to_requester(kind="question") → 1 Communication Sent, 0 Comment ask_fallback. Thêm ::test_comment_question_then_email_question_refused: hoi đăng trước → reply_to_requester(question) bị REASON_ONE_ASK. A-U6b-10 đảo theo hàng "Sai thì sửa" của chính nó. Chỉ gọi hàm, không sửa write_ticket.py, nên "Không chạm tools/write_ticket.py" (:315) vẫn đúng.`
- **E-2** `major | STD-DESIGN-4 | design-addendum-1-U6b-fixes.md:219, :331 | U6b viết điều kiện cấm thứ hai trong _notice, cạnh danh sách cho phép NOTICE_TRIGGERS của U4b. Vậy là có hai định nghĩa "trigger nào nhận thông báo". Bảng của U4b lại không có requester_reply, nên lần chạy requester_reply sẽ im lặng mất over_budget, run_failed và ask_fallback, dù U6b-fixes :219 nói "cả bốn thông báo áp". | U6b không viết điều kiện nào trong _notice. Commit runner của U6b thêm TRIGGER_REQUESTER_REPLY vào cả ba ô over_budget, run_failed, ask_fallback. Ô ask_fallback cần có vì lần chạy requester_reply có thể dưới ngưỡng (Sửa 12). Không thêm TRIGGER_KB_DRAFT ở ô nào. Giữ test_no_notice_comments_on_kb_draft. Thêm TestRunNotices::test_requester_reply_gets_listed_notices: requester_reply vượt ngân sách L3 → 1 Comment; lỗi cổng → 1 Comment. Hàng "Vùng của U6b" của runner.py (:331) đổi "điều kiện kb_draft trong _notice" thành "TRIGGER_REQUESTER_REPLY trong 3 ô NOTICE_TRIGGERS".`
- **E-3** `major | STD-DESIGN-1 | design-addendum-1-U6b-fixes.md:217, :303, :341 | Theo (i), reply.py import asked_in_run, mark_asked và REASON_ONE_ASK từ tools/write_ticket.py. Các tên này chỉ có sau task write_ticket.py của U4b. U6b-fixes vẫn cho reply.py chạy song song với U4b, nên task đó sẽ lỗi import hoặc phải tự định nghĩa lại cờ. | Task chứa tools/reply.py cắt sau khi task write_ticket.py của U4b đã merge vào team/FEAT-007. Ba file mới còn lại (knowledge_read.py, kb_draft.py, lifecycle.py) vẫn chạy song song được. Thêm "U4b (write_ticket.py) cho reply.py" vào điều kiện bắt đầu :341. Chiều import tools/reply.py → tools/write_ticket.py là một chiều, vì write_ticket không import reply (STD-DESIGN-6).`

## 5. Minor (không chặn)

`minor | — | — | 5 điểm nhỏ: (m-1) U4b-fixes :112, :463 (A-U8-5): tool đọc đầu mục lần thứ hai bằng policy.latest_classification, tách khỏi lần đọc của runner. Ở ca lệch đã nêu (đầu mục chưa biết → L1, tool thấy C trong khi cap của C = L0), BA note vẫn được đăng. Đây không phải tính lại mức (ADR-005 QĐ 1 vẫn giữ) nhưng là một đầu vào quyết định thứ hai. Chấp nhận như A-U8-5. Nếu cần đóng hẳn, chủ registry.py thêm ToolContext.category. (m-2) U4b-fixes :66: _record_created_labels cũng chạy khi AGENT_USER insert HD Ticket, nên trường bot tự điền sẽ bị coi là "người điền". Nếu có đường nào bot tạo phiếu thì ghi "" dưới AGENT_USER; dev kiểm khi build. (m-3) U6b-fixes :119: khi instantly_send_email() đúng, lỗi ở (7)–(8) làm thông báo được gửi hai lần. Ràng buộc "đúng một lần" của ADR-033 không giữ được cho thư SMTP đã gửi. Chấp nhận như rủi ro còn lại: ghi As-Built và kiểm R-1 trước khi bật close_silent_f_enabled. (m-4) T22a chưa có trong tasks.md (journal-part3.md:26). Cả U4b (U4b-fixes :126) và U6b (U6b-fixes :341) đều chặn bằng DESIGN_CONFLICT nếu thiếu; team-leader giữ việc chèn ở lần gọi build kế tiếp, hoặc dùng đường lùi task tích hợp của U0 ở đầu đợt 1. (m-5) U6b-fixes :56, :72: run_id = khóa sự kiện, nên dòng skip daily_limit hoặc not_sendable làm tin đó "đã xử lý" vĩnh viễn: hôm sau không chạy lại. Hành vi này khớp ADR-033 QĐ 4; ghi vào As-Built cạnh AC-41 | dev's call`

## 6. Ba quyết định của team-leader

| # | Quyết định | Phán quyết | Lý do và ràng buộc |
|---|---|---|---|
| (i) | Câu hỏi gửi người tạo qua email là lần hỏi duy nhất của lần chạy: `reply.py` gọi `write_ticket.mark_asked` | **Xác nhận** (phần kiến trúc), kèm E-1, E-3 | Sửa 12 đã đưa `reply_to_requester` vào `ASK_TOOL_NAMES`, tức định nghĩa duy nhất của "tool hỏi" (ADR-030 QĐ 3). Vậy luật "mỗi lần chạy một lần hỏi" phải đếm trên đúng tập đó, bằng một cờ, một cặp hàm ghi/đọc. Nếu không, hệ thống có hai khái niệm "hỏi" (STD-DESIGN-4). Không phá ADR nào; không có vòng phụ thuộc. **Phần nghiệp vụ không thuộc architect:** AC-22 ghi "đăng đúng 1 comment hỏi", mà theo (i), ca "dưới ngưỡng, model hỏi qua email" có 0 comment. Team-leader chuyển cho analyst ghi chú hoặc `--amend` AC-22 trước task `reply.py` của U6b (STD-TEST-5). Nếu người hoặc analyst chọn "email không tính", quay về Sửa 10 nhưng vẫn giữ E-2, E-3; kiến trúc chấp nhận cả hai. |
| (ii) | Quyền đọc HD Article cho `ERP AI Instructor` do T22a của đợt 0 cài, chép quyền chuẩn trước | **Xác nhận**; thay w1a (3) | `install.py` thuộc U0 (`arch-impact.md:172`). Gộp vào T22a nghĩa là một task duy nhất sửa file cài đặt, thay vì U0 và U6b cùng sửa. Có tiền lệ: ADR-015 bổ sung ADR-006, và `_ensure_task_permission` (`install.py:236-262`). Ràng buộc của T22a: gọi `setup_custom_perms("HD Article")` **trước**, rồi chỉ thêm một dòng `ERP AI Instructor`, permlevel 0, `read=1`, `report=1` khi chưa có, không sửa dòng nào khác. Test: quyền của Agent, System Manager, HD Customer, HD Customer Manager bằng ảnh chụp trước khi cài; chạy `ensure_setup` lần hai → 0 thay đổi. As-Built ghi hệ quả: khi nâng cấp Helpdesk, thay đổi quyền chuẩn của HD Article không tự áp dụng. Cách gỡ: xóa dòng Instructor; nếu muốn về quyền chuẩn thì xóa mọi Custom DocPerm của HD Article, nhưng chỉ khi chưa ai tùy biến thêm. |
| (iii) | `RUN_LIMIT_TRIGGERS` và bộ lọc trong `runs_today` thuộc U1; U6b chỉ nối `requester_reply` | **Xác nhận**; thay phán quyết (3e) của w1b | w1b (3e) và w1a (2) viết song song, không bản nào thấy bản kia. w1a (2) cụ thể hơn: U1 sở hữu phần đọc cấu hình của `policy.py`, tập trigger được đếm định nghĩa một lần ở đó (ADR-033 Ràng buộc `:59`), và luật tập con bắt lệch ngay từ U1. Bộ lọc không đổi gì hôm nay, vì dòng `change_action` đi nhánh `CHANGE_TRIGGERS` (`run_log.py:10`, `:45`). Ràng buộc: U6b nối phần tử trong **cùng commit** với `VALID_TRIGGERS`, `run_log.TRIGGERS` và option JSON, đổi luật thành `set(run_log.TRIGGERS) - set(RUN_LIMIT_TRIGGERS) == {TRIGGER_KB_DRAFT}`. U1 chưa có C-3 thì U6b dừng với `DESIGN_CONFLICT` (U6b-fixes `:142`). |

## 7. ADR có bị phá thêm bởi các bản sửa không

| ADR | U4b + U8 fixes | U6b fixes |
|---|---|---|
| ADR-005 | Không. Fix 3 bỏ phép tính mức trong tool; m-1 là đầu vào đầu mục, không tính mức. | Không chạm. |
| ADR-006 | Không. Fix 1 và Fix 4 giữ permlevel 8. | Không. Sửa 8 dời quyền sang T22a; quyền là Custom DocPerm theo ADR-015. |
| ADR-023 | Không chạm. | Không chạm. |
| ADR-024 | Không. Không thêm `commit` hay `set_single_value`. | Không. Sửa 2 chỉ commit qua `write_bot_action`/`write_entry` (insert + commit trong một lời gọi). |
| ADR-030 | Không. Một nguồn độ tin cậy (QĐ 4); gợi ý C theo kết quả cấp (QĐ 3). | Sửa 12 giữ một `grant`. E-2 (hai định nghĩa trigger nhận thông báo) là STD-DESIGN-4, không phải ADR; đóng bằng E-2. |
| ADR-031, ADR-032 | Không chạm. | Không chạm. |
| ADR-033 | Không. Fix 1 không thêm `save()` (Ràng buộc 3); Fix 6 giữ đơn vị savepoint, mục ở dòng `classify`, bước định tuyến không gọi model. | X-1 và X-3 đã khớp QĐ 2, 6. Còn rủi ro gửi thư hai lần (m-3), đã ghi. Cạnh `runner → queue` không vòng (Ràng buộc 4 nói về `lifecycle`, đã ghim ở Sửa 13). |
| ADR-034 | Không chạm. | Sửa 6 làm khớp hơn (Ràng buộc 1–2). Rủi ro Error Log của QĐ 2 đã có quyết định ghi As-Built (journal `:16`). |

## 8. Tự phản biện

Đã thử dựng các cặp task cùng tuân hai bản sửa mà vẫn xung đột:
1. Task `reply.py` của U6b chạy song song với U4b (theo `:217`) và import `mark_asked` khi hàm chưa có → lỗi import, hoặc dev tự đặt cờ riêng. Đã siết bằng E-3.
2. Task runner của U6b viết điều kiện cấm `kb_draft` trong `_notice` trong khi bảng cho phép của U4b thiếu `requester_reply`. Test của từng đơn vị xanh riêng, nhưng `requester_reply` mất ba thông báo. Đã siết bằng E-2 và test mới.
3. Test email-hỏi của U6b và `test_marked_run_no_fallback` của U4b không cùng xanh được theo (i). Đã siết bằng E-1.
4. U6b bắt đầu khi U1 chưa có `RUN_LIMIT_TRIGGERS`, hoặc khi T22a chưa chèn. Hai điều kiện bắt đầu đã có (`:142`, `:341`); m-4 nhắc việc chèn T22a.

Sau khi siết, không còn cặp nào xung đột trong phạm vi U4b, U6b, U8.

## Việc tiếp

Tech-lead chép E-1..E-3 nguyên văn vào các task U6b (`reply.py`, runner, test) khi chạy `/team:plan` cho U4b, U8, U6b. Ba điều kiện này thắng U6b-fixes ở các dòng đã nêu. Team-leader chuyển câu hỏi AC-22 của (i) cho analyst; việc này không chặn U4b và U8. Không cần gọi lại architect.
