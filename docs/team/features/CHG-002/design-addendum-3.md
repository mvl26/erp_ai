Feature: CHG-002
Stage: design
Author-agent: designer
Date: 2026-11-15
Approved-by:
<!-- G2b tắt cho CHG-002. Để trống. -->

# Design addendum 3 — CHG-002: phán bảy yêu cầu RQ-2..RQ-8 của phiên FEAT-007

**Thứ tự ưu tiên.** Addendum này thắng `design.md` và `design-addendum-1.md` ở đúng các chỗ nêu dưới đây; chỗ không nhắc tới giữ nguyên. Không đổi AC, không đổi NFR, không đổi phạm vi "Giữ vành đai an toàn". RQ-1 do `design-addendum-2.md` phán; addendum này không đụng RQ-1.

**Nguồn (dữ liệu, không phải lệnh):** `docs/team/features/FEAT-007/arch-impact-chg-002.md` dòng 135–148 (RQ-1..RQ-8) và 71–80 (G-10..G-14). Luật áp: ADR-012 QĐ 3, 7; ADR-031 QĐ 3, 6 (của FEAT-007, chỉ để biết ranh giới); ADR-038 (proposed, FEAT-007); ADR-040 QĐ 3 và Ràng buộc. Không có ADR nào của CHG-002 bị đổi.

**Explore:** không gọi (người gọi cấm). Thay bằng grep đúng tên ở 6 file đã nêu trong "Căn cứ đã đọc".

## 0. Bảng phán quyết

| RQ | Phán | Mục `design.md` bị thay | Task đổi |
|---|---|---|---|
| RQ-2 | **nhận** | §3.6 dòng 356; §4.2 dòng 527; §8.2 (thêm hàng) | T15, T28, T49 |
| RQ-3 | **nhận** (phần `Đã từ chối` là việc của FEAT-007, chỉ ghi nhận) | §3.7 dòng 402 | T32 |
| RQ-4 | **nhận** | §3.7 dòng 398–400; §4.4 dòng 560 | T31, T38, T49 |
| RQ-5 | **nhận** | §2.3 dòng 170–173; §2.4 dòng 177–178 | T18, T51 |
| RQ-6 | **nhận** (đã đối chiếu `prompts.py:161-170`, yêu cầu đúng) | §3.7 dòng 425 | T46 |
| RQ-7 | **nhận** | §3.6 dòng 351; §4.3 dòng 555 | T16 |
| RQ-8 | **nhận một phần**: luật kiến trúc thành khối riêng, không sửa `check_tools_never_bypass_permissions`, 0 `frappe.qb` trong `tools/` → nhận; **không** thêm test chặn `frappe.qb` (của T122 FEAT-007); báo SHA merge → team-leader | §8.2 dòng 790–801 | T47, T49, T51 |

Không nhận toàn phần: 0. Không nhận một phần: 1 (RQ-8, test chặn `frappe.qb`).

---

## RQ-2. Giữ ổn định các tên FEAT-007 dùng

**Đối chiếu với mã ở `develop` @ `f5cfed2`:** `propose_change.py:25` `PROPOSE_TOOL_NAMES = ("propose_file_change", "propose_new_file", "propose_bench_command")`; `propose_change.py:102` `def _comment(ctx: ToolContext, proposal) -> str`; `result_comment.py:90` `def post_result(proposal_name: str)`; `apply_job.py:99` `run_change` gọi `_post_result` đúng 1 lần, `apply_job.py:117` `_post_result` gọi `result_comment.post_result` đúng 1 lần; `transitions.py:95` `content_digest(doc)`; `transitions.py:106` `log_step(proposal, step, actor, *, error=None, before=None, after=None)`; `transitions.py:224-236` `finish(name, expected, new_status, *, step, actor, …)`. CHG-002 không đổi tên nào trong số này; `design.md` không có câu nào đổi tên. Yêu cầu là ràng buộc giữ nguyên, nên nhận và ghim bằng test.

**Câu thiết kế mới:**
- §3.6 dòng 356 thay bằng: "`finish(…, *, …, command_results=None)`: `command_results` là tham số **chỉ từ khóa**, đặt sau `*` có sẵn. Ba tham số vị trí `name, expected, new_status` giữ nguyên. `log_step` không đổi chữ ký; nếu cần thêm thì chỉ thêm tham số chỉ từ khóa. Hành vi khác giữ nguyên."
- §4.2 dòng 527 thêm câu: "`run_change` gọi `_post_result` đúng 1 lần (như `apply_job.py:99` hôm nay); `result_comment.post_result(proposal_name)` được gọi đúng 1 lần trong `apply_job.py`, trong `_post_result`. Chữ ký `post_result(proposal_name)` không đổi."
- Thêm vào §3.2 (hợp đồng nội bộ): "Giữ nguyên tên và chữ ký: `propose_change._comment(ctx, proposal)` (liên kết trong đó vẫn dựng bằng `change_link.decision_path`), `PROPOSE_TOOL_NAMES` (ba tên, đúng thứ tự), khóa kết quả tool `ok`, `proposal`, `status`, `comment`, `transitions.content_digest(doc)`, `block.is_block(doc)`."

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Ghim bằng một test `inspect.signature` + AST trong khối luật riêng của CHG-002 (RQ-8) | FEAT-007 (T89, T105, U7a) gọi thẳng các tên này; một đổi tên lặng lẽ chỉ lộ ra lúc gộp nhánh | Chỉ ghi chữ trong design, không test | Gỡ test `test_feat007_names_and_signatures_stable`; không mã sản phẩm nào phụ thuộc vào nó |

**Test thêm:**
- `ARCH::TestChangeBlockRules::test_feat007_names_and_signatures_stable` (T49): `PROPOSE_TOOL_NAMES` bằng đúng bộ ba trên; tham số của `_comment` là `("ctx", "proposal")`; của `post_result` là `("proposal_name",)`; của `content_digest` và `block.is_block` là `("doc",)`; `finish` có đúng ba tham số vị trí `("name", "expected", "new_status")`, mọi tham số khác `KEYWORD_ONLY`; `log_step` có đúng ba tham số vị trí `("proposal", "step", "actor")`, mọi tham số khác `KEYWORD_ONLY`; AST: thân `_comment` có ≥ 1 lời gọi `change_link.decision_path`; trong `apply_job.py` có đúng 1 lời gọi `result_comment.post_result`, và thân `run_change` có đúng 1 lời gọi `_post_result`.
- `TR::TestFinish::test_command_results_is_keyword_only` (T15): gọi `finish(...)` với `command_results` theo vị trí → `TypeError`; theo từ khóa → ghi JSON.
- `PC::TestProposeBlock::test_result_keys_stable` (T28): kết quả thành công có tập khóa đúng `{"ok", "proposal", "status", "comment"}`. Nếu `design-addendum-2.md` (RQ-1) đã thêm test cùng nội dung thì tech-lead giữ một test, không giữ hai.

---

## RQ-3. `result_lines` rẽ theo dạng

**Đối chiếu:** `result_comment.py:81` `result_lines(fields: dict)` nhận dict trường, không nhận `doc`, nên không gọi được `block.is_block(doc)`. `design.md` §3.7 dòng 402–412 mô tả dòng của khối nhưng không nói nhánh nào quyết định.

**Câu thiết kế mới (§3.7, chèn trước dòng 402):**
> `result_lines(fields, *, doc=None)`: tham số mới chỉ từ khóa. `post_result` đọc `doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal_name)` và truyền vào. Dòng riêng của khối (dòng từng mục, dòng lệnh `bench …: mã thoát`, `restart: …`, `việc người còn phải làm: …`) xuất hiện **khi và chỉ khi** `doc is not None and block.is_block(doc)`. Còn lại là dạng cũ, chữ giữ đúng từng byte như CHG-001 (`f5cfed2`). CHG-002 không thêm, không bớt trạng thái nào trong tập trạng thái mà `result_lines` hôm nay nhận; nhánh `Đã từ chối` (chỉ dòng 1) và nhánh loại bản ghi do FEAT-007 U7a thêm **trước** nhánh khối (G-13), CHG-002 không viết chúng.

Phụ thuộc mới `result_comment → block` một chiều (`block.py` không nhập `result_comment`), không tạo vòng (STD-DESIGN-6).

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Thêm `doc=` chỉ từ khóa, quyết bằng `block.is_block(doc)` | Đúng một luật phân dạng cho cả mã (§2.3); FEAT-007 thêm nhánh của họ phía trước mà không đụng nhánh khối | (a) Thêm cờ `is_block` vào `fields`; (b) hàm riêng `block_result_lines` | Đổi sang (b): `post_result` rẽ, `result_lines` trở về chữ ký cũ; test giữ nguyên tên |

**Test thêm (T32):**
- `RC::TestBlockResult::test_block_only_lines_absent_when_not_block`: đề xuất không dòng con, không `command_list`, mỗi trạng thái kết cục hôm nay nhận → không có chuỗi `restart:`, `việc người còn phải làm`, `mã thoát`.
- `RC::TestLegacyResult::test_legacy_text_byte_identical_per_status`: với mỗi trạng thái kết cục hôm nay nhận, chữ của dạng cũ bằng chuỗi ghim chép từ `result_lines` ở `f5cfed2` (thay cho `test_legacy_result_text_unchanged` nếu test đó chỉ phủ một trạng thái; phủ đủ thì giữ tên cũ và thêm vòng lặp trạng thái).

---

## RQ-4. Dòng báo trước restart

**Đối chiếu:** `design.md` §3.7 dòng 398–400 và §4.4 dòng 560 đã đặt `post_restart_notice` ở `result_comment.py`, chỉ khi có `restart`, chữ mở đầu bằng `Đề xuất {tên} đã …` (không phải `kết quả đề xuất`). `result_comment.py:100` hôm nay ghi bằng `frappe.get_doc(TICKET_DOCTYPE, …).add_comment(COMMENT_TYPE_INFO, text)`, dưới user phiên, không `set_user`, không `publish_realtime`, không `new_comment` (grep = 0). Còn thiếu: "đúng 1 chỗ gọi trong `apply_job.py`" và ràng buộc tiền tố.

**Câu thiết kế mới:**
- §3.7 dòng 398 thêm: "`post_restart_notice` ghi comment bằng **cùng** lời gọi `add_comment(COMMENT_TYPE_INFO, text)` như `post_result` (STD-DESIGN-4), dưới user phiên của job. Không gọi `frappe.set_user`, `frappe.publish_realtime`, không phát sự kiện `new_comment`. Chữ **không** mở đầu bằng `kết quả đề xuất` (tiền tố đó dành cho comment kết quả, ADR-038 của FEAT-007)."
- §4.4 dòng 560 thay bằng: "1. Mục 4.4 là **một** hàm của `apply_job.py` dùng cho cả áp dụng và hoàn tác (`expected` là tham số). Hàm này là chỗ **duy nhất** trong `apply_job.py` gọi `result_comment.post_restart_notice`, và chỉ chạy khi `restart` có trong `command_list`. Gửi notice rồi commit DB; comment này có trước lời khởi chạy (AC-46 b)."

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Một hàm restart dùng chung, một chỗ gọi notice | §4.3 bước 7 đã nói "làm mục 4.4", nên đây là gom, không thêm việc; FEAT-007 đếm comment kết quả theo tiền tố | Gọi notice ở hai nhánh áp dụng/hoàn tác | Tách lại hai chỗ gọi và nới luật AST thành "≤ 2" |

**Test thêm:**
- `RC::TestRestartNotice::test_info_comment_session_user_not_result_prefix` (T31): comment `comment_type == "Info"`, `owner == frappe.session.user`, nội dung không mở đầu bằng `kết quả đề xuất`; `frappe.set_user` và `frappe.publish_realtime` (patch) 0 lần gọi.
- `AB::TestRestart::test_no_restart_in_list_zero_notice_comment` (T38): khối không có `restart` → 0 comment notice, 0 lần `launch_restart`, đúng 1 comment kết quả.
- `ARCH::TestChangeBlockRules::test_restart_notice_single_call_site` (T49): AST: `post_restart_notice` được gọi đúng 1 lần trong `apply_job.py`; `result_comment.py` có 0 lần `set_user`, `publish_realtime`, `new_comment`.

---

## RQ-5. Bộ chuyển đổi và dấu không nuốt loại lạ

**Đối chiếu:** `constants.py:32-33` có `CHANGE_KIND_CODE`, `CHANGE_KIND_COMMAND`. `transitions.py:101` `content_digest` đã ném `ValueError` khi `doc` không phải đề xuất (`_require_proposal`), nên ném `ValueError` cho loại lạ là cùng kiểu. `design.md` §2.3 dòng 172 nói dạng cũ "thành 1 mục `Sửa` hoặc `Tạo` từ các trường vô hướng": với một đề xuất loại khác (`file_path` rỗng) mã sẽ dựng một mục rỗng (G-10, G-11).

**Câu thiết kế mới:**
- §2.3, thêm sau dòng 173: "`operations_of(doc)` và `commands_of(doc)` kiểm đầu tiên `doc.change_kind in (CHANGE_KIND_CODE, CHANGE_KIND_COMMAND)`; ngoài tập đó → `ValueError(f"change_kind không hỗ trợ ở đường code: {doc.change_kind!r}")`, áp cho cả hai dạng. Không thêm `except`: lỗi đi theo đường lỗi hiện có của người gọi (STD-ERR-1)."
- §2.4, dòng 178 thêm: "Nhánh dạng cũ chỉ nhận `change_kind` thuộc hai loại trên; loại khác → cùng `ValueError`. Thứ tự rẽ: `block.is_block(doc)` → dấu khối; còn lại → kiểm loại → dạng cũ. FEAT-007 (G-10) chèn nhánh loại bản ghi **trước** cả hai; CHG-002 không viết nhánh đó."
- §6 (đối soát, T51) thêm: "trước khi tính lại dấu, đếm đề xuất có `approved_digest` mà `change_kind` ngoài hai loại trên. Khác 0 → không tính dấu các đề xuất đó, dừng và báo team-leader (site `miyano` dùng chung với FEAT-007; cần nhánh bản ghi G-10 trước)."

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Kiểm loại ở lối vào bộ chuyển đổi và ở nhánh dạng cũ của dấu | Một đề xuất bản ghi lạc vào đường code phải lỗi rõ, không thành commit rỗng; dấu của hai loại hôm nay không đổi byte | Chỉ kiểm ở `run_change` | Gỡ hai dòng kiểm và ba test dưới; dấu của đề xuất cũ không bị ảnh hưởng vì kiểm đứng trước công thức |

**Test thêm (T18):**
- `BLK::TestAdapter::test_unknown_change_kind_raises_value_error`: đề xuất trong bộ nhớ (`frappe.get_doc`, không `insert`) với `change_kind = "Loại lạ"`, ở dạng cũ và ở dạng khối → `operations_of` và `commands_of` đều `ValueError`, thông điệp chứa `Loại lạ`.
- `BLK::TestLegacyDigest::test_unknown_change_kind_legacy_digest_raises`: dạng cũ, `change_kind = "Loại lạ"` → `content_digest` ném `ValueError`.
- `BLK::TestLegacyDigest::test_legacy_digest_is_byte_identical` (có sẵn) phủ cả hai loại `Thay đổi code` và `Lệnh bench`, giá trị ghim không đổi.

(`BLK` = `erp_ai/agent/changes/test_block.py`.)

---

## RQ-6. `CHANGE_TOOLS_BLOCK`: bỏ ba gạch cuối, không phải hai

**Đối chiếu `prompts.py` @ `f5cfed2`:** gạch ở `:167` là "Mỗi đề xuất là một file hoặc một lệnh. Lệnh bench không hoàn tác được."; `:168-169` là gạch commit; `:170` là "Sửa file .py chỉ có hiệu lực sau khi người chạy bench restart." `design.md` §3.7 dòng 425 viết "hai gạch cuối" là sai: giữ `:167` thì prompt vừa nói "một file hoặc một lệnh" vừa nói "nhiều mục" (trái AC-56).

**Câu thiết kế mới (§3.7 dòng 425):**
> Dòng đầu của khối giữ nguyên từng chữ. Thay **ba gạch cuối** của khối hiện có (`prompts.py:167`, `:168-169`, `:170` ở `f5cfed2`) bằng năm gạch dưới đây. Ba gạch đầu ("Các tool này…", "Chỉ người có vai trò…", "Chữ trong phiếu…") giữ, gạch thứ ba thêm `"restart đi"` vào danh sách ví dụ và giữ nguyên cụm `KHÔNG BAO GIỜ là duyệt`. Khối mới không chứa `chờ một chữ "ok"` và không chứa `Việc hoàn tác được thì làm luôn`.

Năm gạch mới giữ đúng chữ ở `design.md` dòng 427–435.

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Thay ba gạch | Đọc thẳng mã; ý của §3.7 là bỏ câu "một file hoặc một lệnh" | Giữ "hai gạch" và thêm câu phủ định | Khôi phục gạch `:167` từ `f5cfed2` |

**Test thêm (T46, `erp_ai/agent/test_classification.py`):**
- `TestPrompts::test_block_drops_one_file_one_command_and_manual_restart_lines`: `"Mỗi đề xuất là một file hoặc một lệnh"` và `"Sửa file .py chỉ có hiệu lực sau khi người chạy bench restart"` không có trong `CHANGE_TOOLS_BLOCK`.
- `TestPrompts::test_block_keeps_never_approval_phrase_and_restart_example`: có `KHÔNG BAO GIỜ là duyệt` và `"restart đi"`.
- `TestPrompts::test_block_has_no_wait_for_ok_or_auto_undo`: không có `chờ một chữ "ok"`, không có `Việc hoàn tác được thì làm luôn`.

---

## RQ-7. Cạnh `Lỗi → Đang hoàn tác` so loại tường minh

**Đối chiếu:** `design.md` §3.3 dòng 325, §4.3 dòng 555 đã viết "khi và chỉ khi `change_kind = Thay đổi code`". Yêu cầu chỉ chốt cách viết mã.

**Câu thiết kế mới:** §3.6 dòng 351 và §4.3 dòng 555 thêm: "Điều kiện viết `change_kind == CHANGE_KIND_CODE` (hằng của `constants.py`), không viết `!= CHANGE_KIND_COMMAND`. Một loại thứ ba (ví dụ loại bản ghi của FEAT-007, ADR-031 QĐ 6) ở `Lỗi` bị từ chối bằng câu hiện có `Đề xuất đang ở trạng thái {status}, không hoàn tác được`."

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| So bằng tường minh | Loại mới không tự động được cạnh hoàn tác mà ADR của nó không cho | So "khác lệnh bench" | Không cần hoàn tác: hai cách cho cùng kết quả với hai loại hôm nay |

**Test thêm (T16):** `TR::TestRequestUndo::test_from_failed_other_kind_refused`: đề xuất code ở `Lỗi`, có `apply_commit_sha`, không `undo_commit_sha`; `frappe.db.set_value(..., "change_kind", "Loại lạ", update_modified=False)` → `request_undo` từ chối đúng câu hiện có, trạng thái vẫn `Lỗi`.

---

## RQ-8. Luật kiến trúc thành khối riêng; SHA merge

**Đối chiếu `erp_ai/tests/test_architecture.py` @ `f5cfed2`:** hàm kiểm `check_tools_never_bypass_permissions` ở `:647`; lớp `TestArchitecture` ở `:4348`; lớp tự kiểm `TestScannersCatchViolations` ở `:5394`. `git grep "frappe\.qb" -- erp_ai/agent/tools/` = 0 dòng. CHG-002 không dự định dùng `frappe.qb` trong `tools/`.

**Câu thiết kế mới (§8.2, thay câu dẫn của bảng dòng 790–801):**
> Mọi luật **mới** của CHG-002 nằm trong một khối riêng ở cuối `test_architecture.py`: các hàm kiểm `check_change_block_*` liền nhau, một lớp mới `TestChangeBlockRules` chứa cả test luật lẫn ca tự kiểm bằng mã mẫu vi phạm. Không sửa thân `check_tools_never_bypass_permissions`; mã mới của CHG-002 trong `tools/` phải qua luật đó như hiện có, không qua được thì dev dừng với `DESIGN_CONFLICT`, không thêm ngoại lệ. Không dùng `frappe.qb` trong `erp_ai/agent/tools/`. Hai test **có sẵn** được mở rộng tại chỗ (không có cách khác vì là hàm có sẵn): `test_fs_writes_only_in_file_writer` (T48) và `_write_argv_problems` của `test_git_commit_add_rm_argv_shape` (T7); `test_bench_allowlist_has_no_git_running_subcommands` (T48) cũng vậy.

Đổi tên test do dời lớp (chỉ tên lớp đổi, nội dung giữ nguyên):

| Tên cũ (`design.md` §8.2, addendum-1 §8.2) | Tên mới |
|---|---|
| `ARCH::TestArchitecture::test_restart_launch_shape` | `ARCH::TestChangeBlockRules::test_restart_launch_shape` |
| `ARCH::TestArchitecture::test_no_sudo_or_supervisorctl_argv` | `ARCH::TestChangeBlockRules::test_no_sudo_or_supervisorctl_argv` |
| `ARCH::TestArchitecture::test_single_text_rule_no_extension_list` | `ARCH::TestChangeBlockRules::test_single_text_rule_no_extension_list` |
| `ARCH::TestArchitecture::test_change_limits_defined_once` | `ARCH::TestChangeBlockRules::test_change_limits_defined_once` |
| `ARCH::TestArchitecture::test_change_file_max_bytes_defined_once_compared_only_in_text_refusal` | `ARCH::TestChangeBlockRules::test_change_file_max_bytes_defined_once_compared_only_in_text_refusal` |
| `ARCH::TestArchitecture::test_search_file_max_bytes_gone` | `ARCH::TestChangeBlockRules::test_search_file_max_bytes_gone` |

Thêm vào lớp mới: `test_feat007_names_and_signatures_stable` (RQ-2), `test_restart_notice_single_call_site` (RQ-4).

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Khối hàm kiểm + một lớp mới ở cuối file | Hai nhánh cùng thêm vào file 6.800+ dòng; khối liền nhau làm xung đột gộp chỉ là nối hai đoạn | Rải test vào `TestArchitecture` như design cũ | Dời các test về `TestArchitecture`; nội dung không đổi |
| **Không** viết test chặn `frappe.qb` trong `tools/`; kiểm bằng bước có đầu ra ở T51 | Luật đó thuộc T122 của FEAT-007; viết hai lần là trùng (STD-DESIGN-4) và xung đột gộp | Thêm test riêng của CHG-002 | Thêm `test_no_frappe_qb_in_tools` vào `TestChangeBlockRules` nếu T122 không vào `develop` |

**Phần "báo SHA merge" vào `note-from-feat-004-session.md`:** việc của team-leader khi CHG-002 vào `develop`. Ghi nhận ở đây, design không làm.

**Một câu chuyển lại phiên FEAT-007 (phần không nhận):** CHG-002 không thêm test chặn `frappe.qb` trong `tools/` vì luật đó thuộc T122 của FEAT-007; CHG-002 chỉ cam kết 0 lần dùng và dán đầu ra `git grep` ở checkpoint T51.

---

## 1. Bảng "tasks.md đổi gì" (cho tech-lead)

| Task | Files thêm | Dòng Returns thêm | Dòng Expect thêm (tên test) | Depends thêm |
|---|---|---|---|---|
| T15 | — | `command_results` là tham số chỉ từ khóa, sau `*` có sẵn; ba tham số vị trí của `finish` và chữ ký `log_step` không đổi (A3 RQ-2) | `TestFinish::test_command_results_is_keyword_only` | — |
| T16 | — | Điều kiện viết `change_kind == CHANGE_KIND_CODE`, không viết "khác lệnh bench"; loại thứ ba ở `Lỗi` bị từ chối bằng câu hiện có (A3 RQ-7) | `TestRequestUndo::test_from_failed_other_kind_refused` | — |
| T18 | `erp_ai/agent/changes/transitions.py` | `operations_of`, `commands_of` (cả hai dạng) và nhánh dạng cũ của `content_digest` chỉ nhận `CHANGE_KIND_CODE`, `CHANGE_KIND_COMMAND`; loại khác → `ValueError` chứa giá trị loại; không thêm `except` (A3 RQ-5) | `TestAdapter::test_unknown_change_kind_raises_value_error`, `TestLegacyDigest::test_unknown_change_kind_legacy_digest_raises`; `test_legacy_digest_is_byte_identical` phủ cả hai loại | — |
| T28 | — | Khóa kết quả tool giữ `ok`, `proposal`, `status`, `comment`; `PROPOSE_TOOL_NAMES` giữ ba tên đúng thứ tự (A3 RQ-2) | `TestProposeBlock::test_result_keys_stable` (bỏ nếu addendum-2 đã có test cùng nội dung) | — |
| T31 | — | Ghi bằng cùng `add_comment(COMMENT_TYPE_INFO, …)` như `post_result`, dưới user phiên; 0 `set_user`, `publish_realtime`, `new_comment`; chữ không mở đầu bằng `kết quả đề xuất` (A3 RQ-4) | `TestRestartNotice::test_info_comment_session_user_not_result_prefix` | — |
| T32 | — | `result_lines(fields, *, doc=None)`; `post_result` truyền `doc`; dòng riêng của khối khi và chỉ khi `block.is_block(doc)`; dạng cũ đúng từng byte `f5cfed2` cho mọi trạng thái hôm nay nhận; không thêm/bớt trạng thái (A3 RQ-3) | `TestBlockResult::test_block_only_lines_absent_when_not_block`, `TestLegacyResult::test_legacy_text_byte_identical_per_status` | — |
| T38 | — | Bước restart là **một** hàm dùng chung áp dụng/hoàn tác, chỗ duy nhất gọi `post_restart_notice`, chỉ khi có `restart` (A3 RQ-4) | `TestRestart::test_no_restart_in_list_zero_notice_comment` | — |
| T46 | — | Thay **ba** gạch cuối (`prompts.py:167`, `:168-169`, `:170` ở `f5cfed2`), không phải hai; giữ `KHÔNG BAO GIỜ là duyệt`; không có `chờ một chữ "ok"`, `Việc hoàn tác được thì làm luôn` (A3 RQ-6) | `TestPrompts::test_block_drops_one_file_one_command_and_manual_restart_lines`, `test_block_keeps_never_approval_phrase_and_restart_example`, `test_block_has_no_wait_for_ok_or_auto_undo` | — |
| T47 | — | Hai test mới đặt trong lớp mới `TestChangeBlockRules` ở khối riêng cuối file, kèm ca tự kiểm trong cùng lớp; không sửa `check_tools_never_bypass_permissions` (A3 RQ-8) | đổi tên: `TestChangeBlockRules::test_restart_launch_shape`, `TestChangeBlockRules::test_no_sudo_or_supervisorctl_argv` | — |
| T48 | — | Không đổi (mở rộng test có sẵn tại chỗ là ngoại lệ đã ghi ở A3 RQ-8) | — | — |
| T49 | — | Mọi test mới vào `TestChangeBlockRules`; thêm hai luật: tên và chữ ký FEAT-007 dùng (A3 RQ-2), một chỗ gọi `post_restart_notice` và 0 `set_user`/`publish_realtime`/`new_comment` ở `result_comment.py` (A3 RQ-4) | đổi tên: `TestChangeBlockRules::test_single_text_rule_no_extension_list`, `…::test_change_limits_defined_once`, `…::test_change_file_max_bytes_defined_once_compared_only_in_text_refusal`, `…::test_search_file_max_bytes_gone`; thêm `…::test_feat007_names_and_signatures_stable`, `…::test_restart_notice_single_call_site` | T28, T30, T38 |
| T51 | — | Đối soát: đếm đề xuất có `approved_digest` mà `change_kind` ngoài hai loại; khác 0 → dừng, báo team-leader (A3 RQ-5). Hai bước có đầu ra: `git grep -n "frappe\.qb" -- erp_ai/agent/tools/` = 0 dòng; `git diff f5cfed2 -- erp_ai/tests/test_architecture.py` không có hunk trong thân `check_tools_never_bypass_permissions` (A3 RQ-8) | dán hai đầu ra trên vào dòng progress | — |

Số task đổi: 12 (T15, T16, T18, T28, T31, T32, T38, T46, T47, T49, T51 đổi nội dung; T48 chỉ ghi chú "không đổi"). Không thêm task, không bớt task.

## 2. Touchpoints

Không thêm file mã mới, không bớt file. Mọi file đã có ở §7 `design.md`: `transitions.py`, `block.py`, `result_comment.py`, `apply_job.py`, `propose_change.py`, `prompts.py`, `test_transitions.py`, `test_block.py`, `test_result_comment.py`, `test_apply_block.py`, `test_propose_change.py`, `test_classification.py`, `erp_ai/tests/test_architecture.py`. Thay đổi duy nhất ở cấp task: T18 thêm `erp_ai/agent/changes/transitions.py` (đã là touchpoint của T1, T15–T17).

**Đối chiếu file mới với `allowed_new_file_roots` = `["erp_ai", "docs", ".github"]`:**
```
(không có file mã mới)
docs/team/features/CHG-002/design-addendum-3.md -> docs
```
**Đối chiếu với `protected_paths` = `[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`:** 0 khớp.

## 3. Test plan sau addendum

### 3.1 Hàng thêm của bảng tiêu chí (chỉ thêm đường lỗi/biên; test chính giữ nguyên)
| Tiêu chí | Test thêm |
|---|---|
| AC-42 (tương thích dạng cũ, cạnh hoàn tác) | `BLK::TestAdapter::test_unknown_change_kind_raises_value_error`; `BLK::TestLegacyDigest::test_unknown_change_kind_legacy_digest_raises`; `TR::TestRequestUndo::test_from_failed_other_kind_refused` |
| AC-46 (b) (comment trước restart) | `RC::TestRestartNotice::test_info_comment_session_user_not_result_prefix`; `AB::TestRestart::test_no_restart_in_list_zero_notice_comment` |
| AC-48 (comment đề xuất) | `PC::TestProposeBlock::test_result_keys_stable` |
| AC-49 (comment kết quả) | `RC::TestBlockResult::test_block_only_lines_absent_when_not_block`; `RC::TestLegacyResult::test_legacy_text_byte_identical_per_status`; `TR::TestFinish::test_command_results_is_keyword_only` |
| AC-56 (prompt) | `TestPrompts::test_block_drops_one_file_one_command_and_manual_restart_lines`; `…::test_block_keeps_never_approval_phrase_and_restart_example`; `…::test_block_has_no_wait_for_ok_or_auto_undo` |
| AC-57 (hàng của addendum-1) | cột đường lỗi đổi tên thành `ARCH::TestChangeBlockRules::test_no_sudo_or_supervisorctl_argv` |

### 3.2 Luật kiến trúc: hàng thêm
| Luật | Tên test |
|---|---|
| Tên và chữ ký FEAT-007 dùng giữ nguyên; 1 lời gọi `post_result` trong `apply_job.py`, 1 lời gọi `_post_result` trong `run_change` | `ARCH::TestChangeBlockRules::test_feat007_names_and_signatures_stable` |
| `post_restart_notice` gọi đúng 1 chỗ trong `apply_job.py`; `result_comment.py` có 0 `set_user`, `publish_realtime`, `new_comment` | `ARCH::TestChangeBlockRules::test_restart_notice_single_call_site` |

### 3.3 Đối chiếu AC (spec ↔ test plan) sau addendum
```
spec:      AC-36 AC-37 AC-38 AC-39 AC-40 AC-41 AC-42 AC-43 AC-44 AC-45 AC-46 AC-47 AC-48 AC-49 AC-50 AC-51 AC-52 AC-53 AC-54 AC-55 AC-56 AC-57 | NFR-12 NFR-13 NFR-14 NFR-15
test plan: AC-36 AC-37 AC-38 AC-39 AC-40 AC-41 AC-42 AC-43 AC-44 AC-45 AC-46 AC-47 AC-48 AC-49 AC-50 AC-51 AC-52 AC-53 AC-54 AC-55 AC-56 AC-57 | NFR-12 NFR-13 NFR-14 NFR-15
```
22/22 AC và 4/4 NFR vẫn đủ. Addendum chỉ **thêm** test và đổi tên lớp của 6 test kiến trúc; không test nào bị gỡ; không AC nào mất test. Phạm vi "Giữ vành đai an toàn" không đổi.

## Assumptions decided by the team (thêm)
| # | Chọn | Vì | Phương án khác | Sai thì sửa thế nào |
|---|---|---|---|---|
| D-20 | `result_lines` nhận `doc=` chỉ từ khóa | `result_lines(fields)` hôm nay không thấy dòng con | Cờ trong `fields` | Đổi sang hàm riêng `block_result_lines` |
| D-21 | Kiểm loại ở cả hai dạng của bộ chuyển đổi | Đơn giản, chặt hơn yêu cầu (chỉ dạng cũ là bắt buộc) | Chỉ dạng cũ | Bỏ kiểm ở nhánh dạng khối |
| D-22 | Test chặn `frappe.qb` để cho T122 FEAT-007 | Tránh trùng luật | Viết bản của CHG-002 | Thêm test vào `TestChangeBlockRules` |

Câu hỏi nghiệp vụ: 0. Điểm chờ vai khác: 0 (báo SHA merge là việc team-leader làm sau merge, không chặn build).

## Căn cứ đã đọc (2026-11-15, `develop` @ `f5cfed2`, chỉ đọc)
- `docs/team/features/FEAT-007/arch-impact-chg-002.md:71-80`, `:135-148`.
- `docs/team/features/CHG-002/design.md:167-181`, `:321-438`, `:478-581`, `:790-801`; `design-addendum-1.md` (toàn bộ); `tasks.md:132-153`, `:228-290`, `:322-348` và grep tiêu đề task.
- `erp_ai/agent/prompts.py:150-170`: ba gạch cuối của `CHANGE_TOOLS_BLOCK` là `:167`, `:168-169`, `:170`.
- `erp_ai/agent/changes/transitions.py:95-106`, `:224-236`: `content_digest(doc)`, `log_step(..., *, ...)`, `finish(name, expected, new_status, *, ...)`.
- `erp_ai/agent/changes/result_comment.py:81`, `:90`, `:100`: `result_lines(fields)`, `post_result(proposal_name)`, `add_comment(COMMENT_TYPE_INFO, …)`; 0 `set_user`/`publish_realtime`/`new_comment`.
- `erp_ai/agent/tools/propose_change.py:25`, `:102`; `erp_ai/agent/changes/apply_job.py:99`, `:111`, `:117`; `erp_ai/constants.py:32-33`.
- `erp_ai/tests/test_architecture.py:647`, `:4348`, `:5394`; `git grep "frappe\.qb" -- erp_ai/agent/tools/` = 0 dòng.
