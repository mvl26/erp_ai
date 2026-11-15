Feature: CHG-002
Stage: design
Author-agent: designer
Date: 2026-11-15
Approved-by:
<!-- Cổng: không có (team.py: CHG-002 planned 33/53, READY; chỉ G5, lúc lên prod). -->

# Design addendum 9 — CHG-002 (hẹp: 5 dòng `test-drop:` của `RESTART_NOTE` ở T26 và nhãn "đầu vào cũ bị luật mới từ chối")

Phạm vi: đúng điểm mà addendum 8 để mở (`design-addendum-8.md:134`) và đoạn "Quyết định của tech-lead 14:27" ở `review-26.md:27`. Lệnh gọi ghi ở `docs/team/journal/CHG-002.pending-addendum8.md` dòng 3–4. Addendum này không đổi AC hay NFR, không đổi phạm vi N-1 (`intake.md`), không sửa `design.md` và không viết lại commit nào. Như các addendum trước, câu ở đây **thêm vào** đúng những dòng được dẫn.

Tuân: ADR-040 (một khối, một commit), ADR-011 (bộ chặn một chỗ). Không đổi ADR nào. Designer không chạy `team.py claim`, vì lệnh giao chỉ cho dùng Write (như addendum 8).

**Đã đọc (chỉ đọc, `git show`):** thân commit `77bfc62` (T26: 13 `test-shape`, 14 `test-input`, 5 `test-drop`, 1 `test-new`) và `a70a273` (T26 vòng 2: 2 `test-input`, xóa hằng `RESTART_NOTE` khỏi `test_propose_change.py`). Trên `team/CHG-002`, câu cũ `Sau khi áp dụng cần người chạy bench restart.` chỉ còn ở `change_text.py:248` (nhánh dạng cũ). Câu mới của khối ở `change_text.py:151`. Test ghim câu cũ: `test_change_text.py:144` (hằng), `:249`, `:259`, `:580`, `:661`, `:708`; test DocType `test_erp_ai_change_proposal.py:1006`.

Viết tắt: `PC` = `erp_ai/agent/tools/test_propose_change.py`; `CT` = `erp_ai/agent/test_change_text.py`; `DOC` = `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py`.

---

## A9-1. Xác nhận bỏ 5 khẳng định `RESTART_NOTE` của T26 (căn cứ đã sửa)

**Phán: xác nhận.** Không khôi phục test nào.

**Căn cứ đúng (thay cho câu "hành vi không tới được qua tool trước T28"):**
1. `design.md:390` (§3.7): câu `Sau khi áp dụng cần người chạy bench restart.` chỉ còn cho dạng cũ, vì dạng cũ không có lệnh `restart`.
2. `design.md:815` (§8.3, "Test cũ phải sửa"): câu "cần người chạy bench restart" chỉ còn ở dạng cũ.
3. `FEAT-004/spec.md:567` (Amendment 4, bảng "Dòng cũ không còn hiệu lực"): ghi chú này "thay bởi S-16, A-39". Vì spec đã đổi, test được phép đổi theo (STD-TEST-5).
4. Từ T26, mọi đề xuất do tool tạo là khối (`review-26.md:27`; T26 Returns: "dạng gọi cũ … là 1 mục `edit`; `propose_new_file` đi qua `_propose_block`"). Vì vậy câu cũ không bao giờ xuất hiện trên comment do tool tạo, kể cả sau T28. Sau T28, khối có `.py` mang dòng mới `Sau khi áp dụng, hệ thống sẽ restart bench (lệnh cuối).` (`change_text.py:151`) chứ không mang câu cũ. Lý do "trước T28" vì thế sai căn cứ, như reviewer đã ghi.
5. Phần "phủ lại bởi T28 `test_py_block_with_migrate_restart_stored_in_order`" trong 5 dòng cũng sai. Test đó ghim thứ tự `command_list`, không ghim comment. Danh sách phủ đúng ở mục dưới.

**Vì sao đây không phải L-2c (addendum-4):** L-2c dùng khi một luật chặn bị gỡ làm đầu vào cũ thành hợp lệ, và dòng bị bỏ có bản trùng trong Expect. Ở đây không có luật nào bị gỡ. Đây là khẳng định về một **hành vi mà design đã gỡ trên đường của tool**, nên nó theo luật mới L-3b (A9-2).

**Phần còn lại của câu cũ (dạng cũ) vẫn được ghim, đã xanh trên `team/CHG-002`:**
- `CT::TestProposalNotes::test_notes_python_file_needs_restart`: dạng cũ có `.py` ra đúng `[BRANCH_NOTE, UPSTREAM_NOTE, RESTART_NOTE]`, có và không có commit áp dụng;
- `CT::TestBlockNotes::test_legacy_py_note_only_for_legacy`: khối có `.py`, có hoặc không có `[migrate, restart]`, **không** mang câu cũ; dạng cũ giữ đúng output cũ;
- `CT::TestRestartLabel::test_label_is_last_line`: dạng cũ, câu cũ đứng trước nhãn restart;
- `DOC::TestChangeProposalMethods::test_form_data_per_state` (biến `restart`, `:1006`): dữ liệu form của dạng cũ.

**Test mang AC-48 sau khi bỏ** (dòng "sẽ restart" khi và chỉ khi danh sách có `restart`, R-6, `design.md:75`):
- ở mức comment trên phiếu: `PC::TestBlockComment::test_restart_line_iff_restart_listed` (T30 Expect, theo `design.md` §8.1 hàng AC-48);
- ở mức ghi chú: `CT::TestBlockNotes::test_restart_line_iff_restart_listed` (T20, đã xanh);
- test chính của AC-48 không đổi: `PC::TestBlockComment::test_comment_counts_paths_delete_rename_lines_commands_restart_note` (T30).

**Thêm cho T30 (để đường tool ghim lại điều mà 5 dòng cũ từng ghim, theo chiều đúng):** `PC::TestBlockComment::test_restart_line_iff_restart_listed` thêm một khẳng định. Comment trên phiếu của (a) khối có 1 mục `.py` với `[migrate, restart]` và (b) khối chỉ có lệnh `[restart]` chứa câu `Sau khi áp dụng cần người chạy bench restart.` **0 lần** và dòng `Sau khi áp dụng, hệ thống sẽ restart bench (lệnh cuối).` **đúng 1 lần**. Hai chuỗi được viết dạng literal trong test, không import từ `change_text`. Test này chưa có (T30 chưa làm), nên không có test nào bị sửa.

- **Chọn:** xác nhận việc bỏ; ghi lại căn cứ đúng; thêm một khẳng định 0 lần ở T30.
- **Vì:** câu cũ đã bị spec (Amendment 4) và design (§3.7, §8.3) gỡ trên đường của tool. Dạng cũ vẫn được ghim bằng 4 test ở trên. Hành vi thay thế của AC-48 có test ở cả hai mức.
- **Phương án khác:** (1) khôi phục 5 khẳng định: bác, vì chúng sẽ đỏ vĩnh viễn (trái design, chỉ xanh được nếu dựng lại dạng cũ qua tool, mà dạng đó đã bị bỏ); (2) đổi 5 khẳng định thành `assertNotIn`: bác, vì đầu vào của 5 test đã là `.txt` (A9-3), nên `assertNotIn` đúng một cách tầm thường và không ghim gì; khẳng định 0 lần ở T30, trên khối có `.py`, mới có giá trị.
- **Sai thì hoàn tác:** nếu một addendum sau bác A9-1, tech-lead chèn task sau T30 với touchpoint `PC`. Task đó khôi phục 5 khẳng định trong `PC::TestProposeChange::test_file_change_creates_pending_proposal_and_comment_without_touching_disk`, `test_comment_escapes_html_and_adds_restart_note_for_py`, `test_core_app_proposal_created_when_listed`, `test_comment_shows_branch_upstream_ahead_and_core_warning`, `test_non_core_app_comment_has_no_core_warning`, trên đề xuất dạng cũ dựng trực tiếp (như `self.code_proposal(...)` của A8-5), và commit với dòng `test-restore: … (addendum-<n>)`.

---

## A9-2. Luật L-3: test có đầu vào từng được nhận, nay bị một luật mới của CHG-002 từ chối

Luật này bổ sung cho L-1 (addendum-2) và L-2 (addendum-4); L-1 và L-2 giữ nguyên. Áp cho T26 (đọc lại theo A9-3) và cho mọi task sau gặp ca này.

**Ranh giới:**
- Cùng đầu vào, trước bị từ chối, nay vẫn bị từ chối nhưng với lý do khác → **L-1**.
- Cùng đầu vào, trước bị từ chối, nay được nhận (luật bị gỡ) → **L-2**.
- Cùng đầu vào hoặc cùng phần dựng, **trước được nhận** (hoặc trước đi tới được bước mà test kiểm), **nay bị chặn sớm hơn** bởi một luật hoặc một bước **mới** của CHG-002 (ví dụ R-5 `change_guard.PY_NEEDS_RESTART`; bước đọc và áp dụng mục ở §4.1 bước 2, nay chạy trước kiểm git ở bước 3) → **L-3**.

**L-3a. Đổi đầu vào hoặc phần dựng (ưu tiên 1).** Dùng khi mục đích của test không phải luật mới. Phải đủ bốn điều kiện:
1. Đầu vào hoặc phần dựng mới được **mọi** luật hiện hành nhận, ở cùng thời điểm và qua cùng hàm như dòng cũ. Riêng ca bước mới chạy sớm hơn: phần dựng mới vẫn đi tới đúng lý do cũ.
2. Mọi assertion giữ nguyên từng byte. Chỉ được đổi giá trị tự đi theo đầu vào (ví dụ literal đã escape của đường dẫn).
3. Đổi ít nhất có thể. Ưu tiên đổi đuôi `.py` → `.txt` cùng thư mục, hoặc thêm đúng phần nội dung mà bước mới cần.
4. Nếu đổi phần dựng vì một hàm bị xóa (ví dụ `_code_values`), vá hàm còn sống ở cùng chỗ của luồng (ví dụ `_insert`) với cùng giá trị giả.

**L-3b. Bỏ khẳng định về hành vi mà design đã gỡ trên đường đó (ưu tiên 2).** Chỉ dùng khi đủ ba điều kiện:
1. Có một dòng của `design.md` hoặc của addendum, và một dòng của spec, nói rõ hành vi đó không còn trên đường mà test đi qua. Phải dẫn `file:dòng`.
2. Phần hành vi còn sống (ví dụ dạng cũ) có ít nhất một test đã xanh ghim nó.
3. Hành vi thay thế có test trong Expect của một task (dẫn tên task).
Chỉ bỏ khẳng định đó. Không bỏ cả test, không bỏ test ghim AC ở §8.1. Thiếu một trong ba điều kiện → `DESIGN_CONFLICT`.

**Khi không dùng được L-3a hay L-3b:** nếu mục đích của test chính là ca chấp nhận mà luật mới nay chặn, và không đầu vào nào giữ được mục đích đó → `DESIGN_CONFLICT`, nêu tên test. Ca từ chối của luật mới là **test mới** (`test-new:`), không sửa test cũ.

**Định dạng dòng trong thân commit** (cùng chỗ với `test-shape:`, `test-input:`, `test-accept:`, `test-drop:`; mỗi test hoặc dòng subTest một dòng):
- `test-input: <file>::<Lớp>::<test>[<nhãn dòng>] — <đầu vào/phần dựng cũ> → <đầu vào/phần dựng mới>; kết quả kỳ vọng không đổi — luật mới <HẰNG hoặc "§x.y bước n"> chặn đầu vào cũ — design §x.y (addendum-9 L-3a)`
- `test-drop: <file>::<Lớp>::<test>[<dòng>] — bỏ <khẳng định> — hành vi bị gỡ trên đường này: <design file:dòng>, <spec file:dòng>; dạng còn lại ghim bởi <file>::<Lớp>::<test>; thay thế ghim bởi <file>::<Lớp>::<test> (<task>) — (addendum-9 L-3b)`

Dòng tiến độ trong `tasks.md`: `L-1: <n>, L-2: <m>, L-3: <k> (L-3a: <a>, L-3b: <b>)`. Reviewer đối chiếu từng dòng với L-3 và STD-TEST-5; dòng không khớp là lỗi chặn merge (như L-1 điểm 5). Test ngoài touchpoint: dev chỉ được tự sửa theo L-3a; L-3b ngoài touchpoint → `DESIGN_CONFLICT` (như L-2).

- **Chọn:** thêm một luật thứ ba, có hai cách theo thứ tự, mỗi cách một dạng dòng; đuôi `(addendum-9 L-3a|L-3b)` để máy đếm được.
- **Vì:** L-2 chỉ có chiều "luật bị gỡ". Chiều ngược lại (luật mới chặn đầu vào cũ) đã gặp 16 lần ở T26 và chưa có dạng; 5 dòng `test-drop:` phải mượn dạng L-2c, không khớp `addendum-4:39`.
- **Phương án khác:** (1) gộp vào L-2 với nhãn tự do "(luật mới)": bác, vì reviewer không đối chiếu máy móc được; (2) xếp vào L-1: bác, vì L-1 là đổi giá trị ghim với cùng đầu vào, còn ở đây đầu vào đổi.
- **Sai thì hoàn tác:** một addendum sau thay A9-2. Các dòng đã chấm theo L-3 giữ nguyên, như L-2.

---

## A9-3. Lý do đã sửa ghi ở đâu (commit đã merge không viết lại)

**Chỗ ghi chính thức là bảng dưới đây của addendum này.** Không amend, không rebase, không force-push (STD-GIT-4), không tạo commit rỗng, không dùng `git notes` (notes không đi theo lần push thường và không có slot `cmd.*`). Tech-lead thêm một dòng dưới T26 trong `tasks.md` (designer không sửa `tasks.md`). qa ở verify và As-Built dẫn A9-3 khi đọc thân `77bfc62` và `a70a273`.

**Đọc lại 5 dòng `test-drop:` của `77bfc62`** (một dạng chung; chỉ `<khẳng định>` khác nhau, lấy nguyên chữ từ thân commit):

`test-drop: erp_ai/agent/tools/test_propose_change.py::TestProposeChange::<test> — bỏ <khẳng định> — hành vi bị gỡ trên đường này: design.md:390 (§3.7), design.md:815 (§8.3), FEAT-004/spec.md:567; dạng còn lại ghim bởi erp_ai/agent/test_change_text.py::TestProposalNotes::test_notes_python_file_needs_restart và ::TestBlockNotes::test_legacy_py_note_only_for_legacy; thay thế ghim bởi erp_ai/agent/tools/test_propose_change.py::TestBlockComment::test_restart_line_iff_restart_listed (T30) — (addendum-9 L-3b)`

| `<test>` | `<khẳng định>` |
|---|---|
| `test_file_change_creates_pending_proposal_and_comment_without_touching_disk` | `assertIn("<p>Sau khi áp dụng cần người chạy bench restart.</p>", comment.content)` |
| `test_comment_escapes_html_and_adds_restart_note_for_py` | `assertIn(restart, python_comment)` |
| `test_core_app_proposal_created_when_listed` | `RESTART_NOTE` trong `assert_in_order([branch, NO_UPSTREAM_NOTE, CORE_WARNING, RESTART_NOTE])` |
| `test_comment_shows_branch_upstream_ahead_and_core_warning` | `RESTART_NOTE` trong `assert_in_order([branch, upstream, CORE_WARNING, RESTART_NOTE])` |
| `test_non_core_app_comment_has_no_core_warning` | `RESTART_NOTE` trong hai danh sách `assert_in_order` |

Chữ "(quyết định tech-lead 14:27, chờ designer xác nhận)" được đọc là: đã xác nhận bởi A9-1.

**Đọc lại 16 dòng `test-input:` có đuôi "luật mới":** nội dung (cũ → mới, tên test) đúng và giữ nguyên. Chỉ đuôi được đọc lại:
- 13 dòng `PY_NEEDS_RESTART` của `77bfc62` (hằng module `REL` và 12 test): đuôi "`kết quả kỳ vọng không đổi — đầu vào từng được nhận nay bị luật mới từ chối (PY_NEEDS_RESTART) — design §3.2 bước 4, §3.8 (D-3)`" đọc là "`kết quả kỳ vọng không đổi — luật mới change_guard.PY_NEEDS_RESTART chặn đầu vào cũ — design §3.2 bước 4, §3.8 (addendum-9 L-3a)`".
- 1 dòng `PC::TestProposeChange::test_git_refusal_creates_zero_proposals[path=path] (PATH row)` của `77bfc62`: đọc là "`… luật mới §4.1 bước 2 chặn đầu vào cũ — design §4.1 bước 2–3 (addendum-9 L-3a)`".
- 2 dòng của `a70a273` (`erp_ai/agent/changes/test_apply_job.py::TestCommitCrossChecks::test_commit_metadata_has_no_email_url_or_token`, `::TestNoKeyLeak::test_fake_key_never_in_proposal_result_log_comment`): đọc là "`… luật mới change_guard.PY_NEEDS_RESTART chặn đầu vào cũ — design §4.1, §4.3 (addendum-9 L-3a; phần dựng dạng cũ theo addendum-8 A8-5)`".

**Đếm đã sửa của T26** (cả hai commit): `L-1: 13, L-2: 0, L-3: 21 (L-3a: 16, L-3b: 5), test-new: 1`.

- **Chọn:** addendum là chỗ ghi; `tasks.md` chỉ trỏ tới nó.
- **Vì:** lịch sử đã merge (`a034a2d`) không đổi; một chỗ đọc duy nhất, nằm cạnh luật mà nó áp.
- **Phương án khác:** `git notes`, bị bác như trên; commit "sửa nhãn" trên T28: bác, vì trộn nhãn của hai task và trái "commit mới nhất mang danh sách đầy đủ **của task đó**" (addendum-4 L-2).
- **Sai thì hoàn tác:** xóa dòng trỏ trong `tasks.md`; thân commit cũ vẫn còn nguyên.

---

## A9-4. T28, T29, T30 có phải dùng nhãn mới không

**Có, nhưng chỉ cho dòng thuộc L-3.** Dòng L-1 dùng `test-shape:` (addendum-2); dòng L-2 dùng dạng của addendum-4; dòng L-3 dùng dạng A9-2. Commit mới nhất của mỗi task chỉ mang danh sách **của task đó**, không chép lại hay sửa dòng của T26 (đã có A9-3). Dòng tiến độ của mỗi task ghi thêm `L-3: <k>`; nếu không có ca nào thì ghi `L-3: 0`.

Dự kiến theo Returns hiện có (dev vẫn phải đối chiếu từng test đỏ):
- **T28:** ba dòng `test-drop` và một `test-shape` của addendum-6 giữ L-2c/L-1, vì `restart` thật sự được mở. `PC::TestProposeBlock::test_py_without_commands_refused_until_commands_exist` vẫn xanh nếu không truyền `commands`, nên không cần dòng nào. Các test T26 đã đổi sang `.txt` giữ nguyên: không đổi ngược về `.py`, vì đổi ngược không thêm độ phủ. Nếu luật vị trí `restart` của `check_block` chặn một đầu vào cũ đang được nhận → L-3a.
- **T29:** bỏ ba giới hạn là L-2 (đã ghi ở T29). Nếu `EDIT_SHAPE` chặn một đầu vào cũ đang được nhận → L-3a.
- **T30:** câu đầu và ghi chú của comment đổi với cùng đầu vào là L-1. Nếu một test cũ khẳng định một câu mà §3.7 gỡ khỏi comment của khối → L-3b, theo đúng ba điều kiện.

---

## Touchpoint thêm theo task

| Task | Touchpoint thêm | Expect đổi |
|---|---|---|
| T26 | không (đã merge; không đổi mã hay test) | không; tech-lead thêm dòng trỏ "Nhãn commit đọc lại theo `design-addendum-9.md` A9-3: L-1: 13, L-2: 0, L-3: 21 (L-3a: 16, L-3b: 5), test-new: 1" |
| T28 | không | không; Returns thêm: "nhãn L-3 theo addendum-9 A9-2 khi có ca" |
| T29 | không | không; Returns thêm như T28 |
| T30 | không (`PC` đã là touchpoint) | `PC::TestBlockComment::test_restart_line_iff_restart_listed` thêm khẳng định của A9-1 (câu cũ 0 lần, dòng mới đúng 1 lần, cho khối `.py` + `[migrate, restart]` và khối chỉ `[restart]`); Returns thêm như T28 |

Đối chiếu file mới: addendum này không thêm file mã hay file test nào. File duy nhất được tạo là `docs/team/features/CHG-002/design-addendum-9.md`, nằm dưới `docs/team/**` (vai designer chỉ ghi ở đó); nó không nằm trong `protected_paths`.

## AC bị ảnh hưởng

**Không có.** Danh sách AC-36..AC-57 và NFR-12..NFR-15 ở `design.md:804-805` giữ nguyên (22/22 AC, 4/4 NFR). AC-48 giữ test chính và test phụ của §8.1 hàng AC-48; A9-1 chỉ thêm một khẳng định vào một test phụ chưa viết. Phạm vi N-1 không bị chạm.

## Cách hoàn tác cả addendum

Một addendum sau thay A9-1..A9-4. Các dòng commit đã chấm theo L-3 giữ nguyên. Nếu A9-1 bị bác, làm theo mục "Sai thì hoàn tác" của A9-1 (task khôi phục sau T30, nêu 5 test). Nếu A9-2 bị bác, các dòng L-3 đọc lại theo dạng mới bằng một bảng như A9-3, không viết lại commit. Khẳng định thêm ở T30 bỏ được mà không đổi AC-48, vì test chính của AC-48 không phụ thuộc vào nó.
