Feature: CHG-002
Stage: design
Author-agent: designer
Date: 2026-11-15
Approved-by:
<!-- Cổng: không có (team.py: CHG-002 planned 33/53, READY; chỉ G5, lúc lên prod). -->

# Design addendum 8 — CHG-002 (hẹp: năm điểm mở của T34, T27, T26 sau build lượt 4)

Phạm vi: năm điểm ở `docs/team/journal/CHG-002.pending-build5.md` dòng 2. Không đổi AC, không đổi NFR, không đổi phạm vi N-1 (`intake.md:47`). Không sửa `design.md`; câu của addendum này **thêm vào** hoặc **thay** đúng những dòng được dẫn, như các addendum trước. Thứ tự: A8-1, A8-2 (T34, đường găng T34 → T40) trước.

Tuân: ADR-022 QĐ 6 (nhánh đổi → `Hết hiệu lực`), QĐ 7 (git từ chối → `Lỗi`); ADR-040 (một khối, một repo, một commit; C-2: `file_writer` kiểm lại đường dẫn lúc ghi); ADR-011 (bộ chặn đường dẫn ghi là một chỗ). Không đổi ADR nào.

Nguồn đã đọc (không Explore: lệnh giao hẹp, mọi chỗ cần xem đã biết tên): `design.md` §3.1 dòng 240–250, §3.2 dòng 280–292, §4.2 dòng 478–491, §8.3 dòng 800–815; `design-addendum-4.md` L-2 (dòng 26–43); `design-addendum-7.md` dòng 99–101 (`ITEM_REASON`); `review-26.md`, `review-27.md`, `review-33.md`; `tasks.md` T26, T27, T34–T40, round 40–45; `FEAT-004/spec.md` AC-18, AC-37, AC-39, AC-40; mã đọc bằng `git show`: `86d2f23:erp_ai/agent/changes/apply_job.py` (`_run`, `_recheck_block`, `_precheck_block`, `_apply_code`), `86d2f23:erp_ai/agent/changes/test_apply_block.py`, `0fd89db:erp_ai/agent/changes/apply_job.py` (`_run` của T35, hằng `BLOCK_WRITE_FAILED`), `0fd89db:erp_ai/agent/changes/file_writer.py` (`make_parents`), `a034a2d:erp_ai/agent/tools/change_guard.py` (`check_block`, `OP_PREFIX`, `GuardResult`), `a034a2d:erp_ai/agent/tools/propose_change.py` (dòng 195–300), `a034a2d:erp_ai/agent/tools/test_propose_change.py` (dòng 1029–1033, 1356–1475), `a034a2d:erp_ai/agent/changes/test_apply_job.py` (lớp, dòng 243–300, 372–466, 500–553), thân commit `a70a273`.

Không chạy `team.py claim --stage design`: lệnh giao chỉ cho Write một file và CHG-002 đang ở build lượt 5.

## Explore summary (thay cho Explore, từ các lần đọc ở trên)
- Dạng cũ đi `_run` → `_recheck_block` (bước 2–3, `check_block(legacy=True)`; lý do bước 2 **đã có** tiền tố `mục 1 (path): ` từ T33, `change_guard.py:473` không miễn dạng cũ) → `_apply_code` (bước 4–5 của một file: hash, `read_git_state`, lý do **không** tiền tố). `_precheck_block` chỉ chạy khi `block.is_block(proposal)` (`86d2f23` `_run`, giữ nguyên ở `0fd89db`).
- Test dạng cũ ghim lý do không tiền tố: `test_apply_job.py::TestApplyCode::test_file_changed_since_proposal_is_stale` (`:253`), `::TestApplyCodeSteps::test_target_changed_after_proposal_becomes_stale` (`:523`), `::TestApplyCodeSteps::test_new_file_appeared_meanwhile_becomes_stale` (`:553`), `::TestGitPrecheck::test_git_precheck_fails_at_apply_without_write_or_commit` (`:384-393`, năm lý do `GIT_*` đúng chữ).
- `_precheck_block` (`86d2f23`): HEAD khác → `Lỗi`, `OP_PREFIX` + `source.GIT_ERROR`; nhánh khác → `Hết hiệu lực`, `GIT_BRANCH_CHANGED` không tiền tố. Test: `TestBlockAllOrNothing::test_head_differs_between_paths_error_names_item` (`:412-428`).
- `propose_change.py` (`a034a2d`): `_under_a_folder` sai → `change_guard.PATH_INVALID` ở `_created_op` và `_renamed_op`; `_removed_text` gọi `check_write_path` trước (luật 6 → `PATH_SYMLINK`), rồi `isfile`/`islink` → `NOT_REGULAR_FILE`.
- `make_parents` (`0fd89db`): thành phần đã `lexists` thì `continue`, nên cha là file làm `mkdir` bên dưới lỗi → T35 trả lại, `BLOCK_WRITE_FAILED`.

## Assumptions decided by the team
- Mọi điểm dưới đây là chi tiết kỹ thuật hoàn tác được (lý do, nhãn, test), không phải luật nghiệp vụ; không điểm nào chạm N-1 hay AC-36..AC-57 (đối chiếu ở cuối). Vì vậy không có `NEEDS_ANSWER`.

---

## A8-1 (T34, điểm a). Dạng cũ không đi bước 4–5 của khối; tiền tố mục chỉ cho khối

**Phán:** chọn (b) của `review-33`/round 40: tiền tố `mục n (path): ` ở bước 4–5 chỉ dành cho khối. Dạng cũ giữ bước 4–5 của nó trong `_apply_code`, đúng chữ như trước CHG-002.

**Câu thêm vào `design.md` §4.2, ngay sau bước 5 (dòng 488):**
> Bước 4–5 ở trên là của dạng khối (`_precheck_block`). Đề xuất dạng cũ (một file, `block.is_block` sai) làm bước 4–5 trong `_apply_code` như trước CHG-002: cùng phép so, cùng trạng thái, lý do **không** có tiền tố mục (`TARGET_CHANGED`, `state.refusal`, `GIT_BRANCH_CHANGED` đúng chữ). Ở dạng cũ, tiền tố mục chỉ có ở bước 2 (`check_block`, T33). Ở cả hai dạng, `GIT_BRANCH_CHANGED` không có tiền tố, vì nhánh là của repo chứ không của một mục.

**Vì:** dạng cũ chỉ có một file, nên "mục 1" không cho người đọc thêm gì. AC-37 ("lý do nêu đúng mục") là AC của khối. Năm test dạng cũ ở trên đã ghim chữ không tiền tố, nên giữ nguyên thì 0 test cũ phải sửa: `design.md:808-815` (§8.3) và touchpoint T34 vẫn đúng, không cần thêm `test_apply_job.py`. T35 (`0fd89db`) đã dựa vào việc `_precheck_block` chỉ chạy cho khối. Cách này là thêm, không sửa.

**Phương án khác:** (a) cho dạng cũ cũng qua `_precheck_block` có tiền tố → đổi 3 test `Hết hiệu lực` và 5 dòng `GIT_*` của `test_apply_job.py` (L-1), T34 phải thêm touchpoint, T35/T36 đang xếp chồng phải merge lại. Loại vì giá cao trên đường găng mà người đọc không được thêm thông tin gì.

**Mã:** T34 không đổi dòng mã nào cho A8-1. Có thể (không bắt buộc) đổi câu docstring của `_precheck_block` "(step 5 has no sentence for it)" thành "(design addendum-8 A8-1, A8-2)".

**Test thêm (T34, `erp_ai/agent/changes/test_apply_block.py`):**
- `TestLegacyThroughAdapter::test_legacy_steps_4_5_reasons_have_no_item_prefix`, ba subTest trên `self.legacy(...)` đã duyệt, cùng `patch.object(apply_job, "_precheck_block", wraps=apply_job._precheck_block)`:
  - `[stale]`: ghi đè file `LEGACY_REL` trên đĩa → `(Hết hiệu lực, apply_job.TARGET_CHANGED)` đúng chuỗi;
  - `[git refusal]`: `self.sandbox.hold_index_lock(APP)` → `(Lỗi, source.GIT_LOCKED)` đúng chuỗi;
  - `[branch]`: checkout nhánh khác → `(Hết hiệu lực, apply_job.GIT_BRANCH_CHANGED)` đúng chuỗi;
  - mỗi subTest: spy `_precheck_block` `assert_not_called()`, 0 byte đổi, HEAD không đổi.
- RED bằng đột biến: cho `_run` gọi `_precheck_block` với mọi dạng → `[stale]` đỏ (`mục 1 (…): file đích đã đổi…` != `file đích đã đổi…`). Hành vi đã đúng trên `86d2f23`, nên đây là test ghim (STD-TEST-8 cho nhánh `if block.is_block`), không phải RED của mã mới.

**Touchpoint thêm:** không (T34 vẫn là `apply_job.py`, `test_apply_block.py`).

**Sai thì hoàn tác:** một addendum sau chọn (a); khi đó T34 bỏ điều kiện `if block.is_block(proposal)` trước `_precheck_block`, xóa test trên, và sửa 8 dòng `test_apply_job.py` theo L-1 (`test-shape:`), thêm `test_apply_job.py` vào touchpoint.

## A8-2 (T34, điểm b). HEAD khác nhau giữa các đường dẫn của một khối → `Lỗi`

**Phán:** giữ đúng mã `86d2f23`: `Lỗi`, lý do `OP_PREFIX.format(number=n, path=operation.path) + source.GIT_ERROR`, tức là `mục n (path): không đọc được trạng thái git`. n là mục của đường dẫn **đầu tiên** (theo thứ tự đọc của bước 5: các mục theo `idx`, mỗi mục nguồn trước đích) có HEAD khác HEAD của đường dẫn đầu khối. 0 byte, 0 thư mục, 0 commit, 0 lệnh, 1 dòng nhật ký (`step="fail"`).

**Câu thêm vào `design.md` §4.2 bước 5, sau "Nhớ `old_head`." (dòng 488):**
> Mọi đường dẫn phải cho cùng một HEAD; HEAD đó là `old_head`. Một đường dẫn cho HEAD khác → `Lỗi`, lý do `mục n (path): ` + `source.GIT_ERROR` (mục đầu tiên lệch), 0 byte ghi.

**Vì:** `check_block` đã chặn `BLOCK_TWO_APPS` và `NESTED_REPO`, nên mọi đường dẫn của khối nằm trong một repo. HEAD lệch giữa hai lần đọc chỉ xảy ra khi một thao tác git khác chen vào giữa bước 5. Đó là trường hợp cùng họ với "khóa git đang bị giữ" và "thao tác dở" của AC-18, nên là `Lỗi` (ADR-022 QĐ 7). Bước 4 vừa chứng minh mọi file trùng nội dung đã duyệt, và nhánh vẫn đúng. AC-37 chỉ dành `Hết hiệu lực` cho "nội dung hay nhánh đổi", nên `Hết hiệu lực` ở đây sẽ nói sai là nội dung đã đổi. Không thêm hằng mới, vì một bất biến gần như không chạm tới được không đáng có câu riêng. Lý do có mục gắn vào dòng của mục n trong comment kết quả nhờ `ITEM_REASON` (addendum-7:100).

**Phương án khác:** `Hết hiệu lực` không tiền tố (coi như repo đổi từ lúc đề xuất): loại vì lý do vừa nêu. Một hằng mới `HEAD_MOVED`: loại, vì thêm chữ cho một ca bất biến và buộc T34, T35, T36 merge lại.

**Mã:** không đổi.
**Test:** giữ `TestBlockAllOrNothing::test_head_differs_between_paths_error_names_item` (`:412-428`), không đổi. Không thêm test.
**Touchpoint thêm:** không. Với A8-1, A8-2 đã phán, T34 hết điểm chờ: tech-lead cho dev thêm test của A8-1 trên `team/CHG-002-task-33` (FIX_BASE `86d2f23`); reviewer chấm `review-34.md` vòng 3 rồi merge, theo đúng luật của lượt build.
**Sai thì hoàn tác:** đổi `CHANGE_STATUS_FAILED` thành `CHANGE_STATUS_STALE` ở một dòng của `_precheck_block`, và đổi đối số `status` trong `assert_failed_untouched` của test trên.

## A8-3 (T27, điểm c). Câu từ chối khi thư mục cha là file

**Phán:** chọn hằng mới của tool, không đặt trong `check_write_path`.

**Hằng (thêm vào `erp_ai/agent/tools/propose_change.py`, ngay dưới `EXISTS`):**
```python
PARENT_NOT_DIR = "thư mục cha trên đường dẫn là một file"
```
`_created_op` và `_renamed_op`: `if not _under_a_folder(guard.full_path): return PARENT_NOT_DIR` (thay `change_guard.PATH_INVALID`). Lý do qua tool có tiền tố như mọi mục: `mục n (<path của mục>): thư mục cha trên đường dẫn là một file` (với đổi tên, `<path của mục>` là nguồn, đúng `OP_PREFIX` hiện có).

**Dòng thêm vào bảng §3.1 (sau `EXISTS`):** `PARENT_NOT_DIR` (tool) | `thư mục cha trên đường dẫn là một file` (tạo, đích đổi tên: thư mục có sẵn gần nhất trên đường dẫn là file).
**Câu thêm vào §4.1 bước 2, mục `create` và đích `rename`:** "thư mục có sẵn gần nhất trên đường dẫn không phải thư mục → `PARENT_NOT_DIR`".

**Lúc áp dụng (không đổi mã):** cha bị đổi thành file sau lúc đề xuất thì bước 4 vẫn qua (`lexists` của đích là sai), rồi `make_parents` / `write_atomic` lỗi ở mục đó và T35 trả lại mọi mục. Kết quả là `Lỗi`, lý do `apply_job.BLOCK_WRITE_FAILED.format(number=k, path=<path của mục k>)` = `ghi mục k (path) lỗi, đã trả mọi file về như trước`. Đây là đường "lỗi giữa chừng" của AC-37. Test của T36 `TestBlockAllOrNothing::test_parent_became_file_after_proposal_error_zero_written` ghim đúng chuỗi đó, kèm cây thư mục, HEAD và index trùng trước/sau, 0 commit.

**Vì:** `PATH_INVALID` ("không hợp lệ hoặc nằm ngoài apps/") dẫn model đi sai hướng: đường dẫn ở trong app, chỉ là cha là file. Model cần câu đúng để sửa lời gọi. `check_write_path` là luật về đường dẫn và vành đai (ADR-011). Luật "cha là file" chỉ cần ở lúc đề xuất, vì lúc áp dụng `file_writer` đã từ chối (ADR-040 C-2). Đặt hằng ở tool thì không nới hay đổi bộ chặn, và nằm trong hai file của tool.

**Phương án khác:** (a) giữ `PATH_INVALID` và chỉ thêm câu vào design: 0 mã, nhưng câu vẫn sai nghĩa. (b) đưa luật vào `check_write_path` để `check_block` lúc áp dụng cũng bắt: ngoài touchpoint, đổi thứ tự luật §3.2, và bộ chặn đã có ở `file_writer`. Cả hai bị loại.

**Test (file `erp_ai/agent/tools/test_propose_change.py`):**
- Đổi `TestProposeBlock::test_create_under_a_parent_that_is_a_file_refused`: ba subTest kỳ vọng `propose_change.PARENT_NOT_DIR` thay cho `change_guard.PATH_INVALID`, và thêm `self.assertEqual(propose_change.PARENT_NOT_DIR, "thư mục cha trên đường dẫn là một file")`. RED thật: đổi test trước, chạy sẽ ra `… đường dẫn không hợp lệ hoặc nằm ngoài apps/ != … thư mục cha trên đường dẫn là một file`.
- Test này sinh trong CHG-002 (`fa330af`), không phải test cũ, nên không dùng nhãn L-1/L-2. Thân commit ghi một dòng: `test-ruling: erp_ai/agent/tools/test_propose_change.py::TestProposeBlock::test_create_under_a_parent_that_is_a_file_refused — change_guard.PATH_INVALID → propose_change.PARENT_NOT_DIR — design addendum-8 A8-3`.

**Touchpoint thêm:** không có file mới. Việc này rơi vào task kế tiếp còn mở trên đúng hai file `propose_change.py`, `test_propose_change.py`: T28 (đang dở ở `team/CHG-002-task-28`). T28 đã gửi review thì sang T29 hoặc T30 (cùng hai file); tech-lead chọn. T27 không mở lại: hành vi từ chối của nó đúng, chỉ câu đổi, nên T27 vẫn tick theo kết quả `cmd.test` của đợt merge 16.

**Sai thì hoàn tác:** hai dòng `return` về lại `change_guard.PATH_INVALID`, xóa hằng, test về lại `change_guard.PATH_INVALID`.

## A8-4 (T27, điểm d). Lý do của symlink khi Xóa (và nguồn Đổi tên)

**Phán:** chọn (a) của `review-27` OPEN-2: symlink ở mục Xóa hay nguồn Đổi tên nhận `change_guard.PATH_SYMLINK` từ `check_write_path` luật 6, cả lúc đề xuất lẫn lúc áp dụng. Nhánh `os.path.islink` trong `_removed_text` giữ lại làm lớp phòng thủ, và lớp này trả `NOT_REGULAR_FILE`. Không nới bộ chặn.

**Thay ô mô tả của `NOT_REGULAR_FILE` ở `design.md:245`** (chữ của hằng giữ nguyên):
> `NOT_REGULAR_FILE` | `đường dẫn không phải file thường` (xóa, nguồn đổi tên: thư mục, không tồn tại; symlink ở thành phần cuối đã bị `check_write_path` luật 6 trả `PATH_SYMLINK` trước, `islink` ở đây chỉ là lớp phòng thủ khi bộ chặn để lọt)

Lý do người và model thấy: qua tool là `mục n (path): đường dẫn đi qua symlink`; lúc áp dụng (`check_block`, T33) là `Lỗi`, cùng chuỗi.

**Vì:** luật 6 là một phần của vành đai AC-53 cho cả năm loại mục. Bỏ luật này cho thành phần cuối của mục Xóa (phương án b) là nới vành đai mà không AC nào cần. Cách (a) chỉ là sửa chữ cho design khớp với mã.

**Mã:** không đổi.
**Test (file `erp_ai/agent/tools/test_propose_change.py`; thực hiện cùng task với A8-3):**
- Đổi `TestProposeBlock::test_delete_symlink_refused`: thay `assertFalse` / `startswith` bằng `self.assert_item_refused(item, change_guard.PATH_SYMLINK)` (đúng chuỗi `mục 1 ({APP}/pkg/link.txt): đường dẫn đi qua symlink`), giữ assertion "symlink còn nguyên". Thêm subTest `rename` với nguồn là symlink đó, cùng lý do. Đây là deferred 1 của `review-27`.
- Thêm `TestProposeBlock::test_symlink_past_guard_is_not_regular_file`: `patch.object(change_guard, "check_write_path", side_effect=…)` trả `GuardResult(full_path=<đường dẫn tuyệt đối của link>, rel_path=f"{APP}/pkg/link.txt", app=APP, reason=None)` cho đúng đường dẫn đó, các đường dẫn khác gọi hàm thật. Mục `delete` → `mục 1 (…): ` + `change_guard.NOT_REGULAR_FILE`, 0 đề xuất, 0 comment. RED bằng đột biến: bỏ `or os.path.islink(full)` → test đỏ, vì `isfile` theo symlink nên trả đúng.
- Dòng thân commit: `test-ruling: erp_ai/agent/tools/test_propose_change.py::TestProposeBlock::test_delete_symlink_refused — bất kỳ lý do có tiền tố mục 1 → change_guard.PATH_SYMLINK đúng chuỗi, thêm [rename] — design addendum-8 A8-4`.

**Touchpoint thêm:** không có (cùng task và cùng hai file như A8-3).
**Sai thì hoàn tác:** design.md:245 về lại chữ cũ; nếu có addendum chọn (b), phải có ADR sửa ADR-011 và một ô AC-53, không làm trong phạm vi này.

## A8-5 (T26, điểm e). Xác nhận quyết định 16:00 của tech-lead về hai test của `test_apply_job.py`

**Phán:** xác nhận, không thay. Hai test là `TestCommitCrossChecks::test_commit_metadata_has_no_email_url_or_token` và `TestNoKeyLeak::test_fake_key_never_in_proposal_result_log_comment`. Phần đề xuất và comment vẫn gọi tool (nay là `pkg/mod.txt`). Chặng áp dụng → hoàn tác chạy trên đề xuất dạng cũ dựng trực tiếp (`self.code_proposal(...)` / `make_change_proposal`), cùng file, cùng nội dung, cùng phiếu, và mọi giá trị kỳ vọng giữ từng byte. Mã `a70a273` đã merge ở `a034a2d`, giữ nguyên.

**Vì:** mục đích của hai test ("metadata commit không có email/URL/token", "khóa giả 0 lần trong mọi kho") vẫn còn nguyên. Chỉ phần dựng đổi, vì thứ tự task (T26 trước T39): từ T26 tool chỉ tạo khối, mà hoàn tác khối là T39. Đó là kiểu "đổi phần dựng, đường kiểm vẫn còn" của addendum-4 L-2a. Dạng cũ vẫn là đường được hỗ trợ (T40 `TestLegacyUndo`), nên kiểm nó bằng đề xuất dạng cũ là đúng đối tượng.

**Nhãn:** hai dòng `test-input:` trong thân `a70a273` được chấp nhận như đã viết (có `file::Lớp::test`, phần dựng cũ → mới, "kết quả kỳ vọng không đổi", dẫn design). Không viết lại lịch sử (không amend, không force-push). Từ nay, đổi phần dựng của một test bất biến ngoài đường lỗi dùng đúng định dạng `test-input:` của addendum-4:37, và kết dòng bằng `(addendum-8 A8-5)` thay cho `(addendum-4 L-2a)`.

**Điều kiện của xác nhận (độ phủ của khối phải quay lại):**
- Áp dụng: T36 `TestBlockCommit::test_block_commit_metadata_has_no_email_url_or_token` (đã thêm ở round 45).
- Rò rỉ khóa: T43 `TestNoKeyLeakBlock::test_seeded_key_zero_in_proposal_comment_log_output`.
- **Thêm cho T39** (`erp_ai/agent/changes/test_apply_block.py`, đã là touchpoint của T39): `TestUndoBlock::test_undo_commit_metadata_has_no_email_url_or_token`. Commit hoàn tác của một khối 5 mục: tác giả, người commit và thân commit không có email người, URL hay token; tác giả là `BOT_AUTHOR`. So như test dạng cũ, cho commit hoàn tác.

**Touchpoint thêm:** không (`test_apply_job.py` đã vào touchpoint T26 ở round 42; T39 thêm một tên test trong file đã có).
**Sai thì hoàn tác:** khi T39 merge, hai test có thể quay về đề xuất qua tool → áp dụng → hoàn tác trên khối, bằng một commit `test-input:` ngược, kết bằng `(addendum-8 A8-5)`.

Ngoài năm điểm, phần **không** phán ở đây: định dạng nhãn cho 5 dòng `test-drop:` (`RESTART_NOTE`) của quyết định tech-lead 14:27 (`review-26.md` đoạn "Quyết định của tech-lead 14:27"). Điểm này không nằm trong lệnh giao và vẫn mở.

---

## tasks.md đổi gì (tech-lead ghi; designer không sửa tasks.md)

| Phán | Task | Returns / Receives đổi | Expect (tên test) |
|---|---|---|---|
| A8-1 | T34 | Returns thêm: bước 4–5 có tiền tố mục chỉ cho khối; dạng cũ giữ `_apply_code` không tiền tố | Thêm `TestLegacyThroughAdapter::test_legacy_steps_4_5_reasons_have_no_item_prefix` |
| A8-2 | T34 | Returns thêm: HEAD lệch giữa các đường dẫn → `Lỗi`, `mục n (path): ` + `source.GIT_ERROR` | Giữ `TestBlockAllOrNothing::test_head_differs_between_paths_error_names_item` |
| A8-3 | T28 (hoặc T29/T30, cùng hai file) | Returns thêm: hằng `propose_change.PARENT_NOT_DIR`; `_created_op`, `_renamed_op` trả hằng đó khi cha là file | Đổi `TestProposeBlock::test_create_under_a_parent_that_is_a_file_refused` |
| A8-3 | T36 | Expect đã có: lý do ghim = `BLOCK_WRITE_FAILED.format(number=k, path=…)` | `TestBlockAllOrNothing::test_parent_became_file_after_proposal_error_zero_written` |
| A8-4 | cùng task với A8-3 | Không đổi mã | Đổi `TestProposeBlock::test_delete_symlink_refused` (+ subTest `rename`); thêm `TestProposeBlock::test_symlink_past_guard_is_not_regular_file` |
| A8-5 | T26 (đã merge), T39 | Không đổi mã | T39 thêm `TestUndoBlock::test_undo_commit_metadata_has_no_email_url_or_token` |

## Đối chiếu AC/NFR và test plan
```
spec:      AC-36 AC-37 AC-38 AC-39 AC-40 AC-41 AC-42 AC-43 AC-44 AC-45 AC-46 AC-47 AC-48 AC-49 AC-50 AC-51 AC-52 AC-53 AC-54 AC-55 AC-56 AC-57 | NFR-12 NFR-13 NFR-14 NFR-15
test plan: AC-36 AC-37 AC-38 AC-39 AC-40 AC-41 AC-42 AC-43 AC-44 AC-45 AC-46 AC-47 AC-48 AC-49 AC-50 AC-51 AC-52 AC-53 AC-54 AC-55 AC-56 AC-57 | NFR-12 NFR-13 NFR-14 NFR-15
```
22/22 AC, 4/4 NFR, như `design.md` §8.3. Addendum này không bỏ test nào; chỉ thêm 3 test, đổi chuỗi ghim của 2 test sinh trong CHG-002, và giữ 1 test.

**AC bị ảnh hưởng: không.** Từng điểm:
- A8-1, A8-2: AC-37 (lý do nêu mục, `Hết hiệu lực` / `Lỗi`) giữ nguyên chữ; dạng cũ giữ AC-18 / AC-6 như hôm nay.
- A8-3: AC-39 không liệt kê ca "cha là file". Từ chối là hành vi duy nhất làm được, và T27 đã làm vậy; chỉ câu đổi.
- A8-4: AC-40 ("qua cùng bộ chặn đường dẫn như ghi") và AC-53 giữ nguyên; vành đai không nới.
- A8-5: AC-38 / AC-51 cho khối vẫn được ghim ở T36, T39, T43.
- N-1 (điểm 1–10) không chạm.

AC chạm tới (chỉ thêm test): AC-37 ← A8-1, A8-2 (`erp_ai/agent/changes/test_apply_block.py::TestLegacyThroughAdapter::test_legacy_steps_4_5_reasons_have_no_item_prefix`, `::TestBlockAllOrNothing::test_head_differs_between_paths_error_names_item`); AC-39 ← A8-3 (`erp_ai/agent/tools/test_propose_change.py::TestProposeBlock::test_create_under_a_parent_that_is_a_file_refused`, `erp_ai/agent/changes/test_apply_block.py::TestBlockAllOrNothing::test_parent_became_file_after_proposal_error_zero_written`); AC-40 ← A8-4 (`erp_ai/agent/tools/test_propose_change.py::TestProposeBlock::test_delete_symlink_refused`, `::test_symlink_past_guard_is_not_regular_file`); AC-38, AC-42 ← A8-5 (`erp_ai/agent/changes/test_apply_block.py::TestUndoBlock::test_undo_commit_metadata_has_no_email_url_or_token`).

## Touchpoints (đường dẫn có sẵn, không tạo file mới)
`erp_ai/agent/changes/test_apply_block.py` (T34, T36, T39); `erp_ai/agent/tools/propose_change.py`, `erp_ai/agent/tools/test_propose_change.py` (T28 hoặc task kế trên hai file đó). `erp_ai/agent/changes/apply_job.py`: chỉ docstring, không bắt buộc (T34).

So với `allowed_new_file_roots` = `["erp_ai", "docs", ".github"]`: 0 đường dẫn mã mới. File mới duy nhất là `docs/team/features/CHG-002/design-addendum-8.md`, nằm dưới `docs` → khớp. So với `protected_paths` = `[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`: không đường dẫn nào ở trên khớp.
