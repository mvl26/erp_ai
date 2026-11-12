# Review T25 vòng 2 (scoped re-review) — request-changes

Diff fix: `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006 diff b0df8e3..team/FEAT-006-task-25-rework1 -- erp_ai` (f790a29). Mã sản xuất không đổi.

## Đối chiếu vòng 1

- major 1 (mapping khác mặc định ở test parity): ADDRESSED.
- major 2 (`output_tokens` ở phản hồi không parse được): ADDRESSED (ca `_predict` + ca mức `run`).
- major 3 (A-13, test dựa dữ liệu site): ADDRESSED cho test được nêu.
- minor (comment): ADDRESSED.

## Finding mới (nguyên văn)

major | STD-TEST-6 | `erp_ai/eval/test_run_eval.py:472-482` | The new test `test_run_counts_cut_off_reply_in_token_metrics` seeds no `category_mapping`, so `unclassified == 1` depends on site data. That count only includes the row if it is labeled. `compute_metrics` labels it through `_expected_category(row["ticket_type"], mapping)` (`run_eval.py:36-42,75-78`), and `mapping` comes from the live Single (`run_eval.py:233`). If the site's `ticket_type` for A differs from the default, the row is skipped and the test fails. Same pattern as old finding 3 (A-13). | Fix: move `set_agent_settings(category_mapping=json.dumps(DEFAULT_CATEGORY_MAPPING), routing_rules=make_routing_rules())` into `TestRunEvalRun.setUp` (`:313`); this fixes this test and the deferred tests below.

## Deferred từ reviewer (setUp seed ở trên sửa luôn, không tốn thêm)

STD-TEST-6 / A-13: các test của `TestRunEvalRun` còn đọc mapping/routing sống: `test_run_uses_given_predictions_without_gateway` (:338), `test_run_classifies_rows_without_prediction_and_prints_report` (:347), `test_gateway_error_on_one_row_counts_unclassified_and_run_continues` (:398), `test_unparseable_reply_counts_unclassified` (:416); `test_eval_and_runner_share_classify_request` (:359) gieo mapping nhưng không gieo `routing_rules` (giá trị kỳ vọng không có departments).

## Cannot verify

- Giá trị `category_mapping`/`routing_rules` thật trên `miyano`: dev báo 860 OK chỉ cho thấy site hiện khớp mặc định.
