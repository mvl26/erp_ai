Feature: CHG-002
Stage: design
Author-agent: designer
Date: 2026-11-15
Approved-by:
<!-- Cổng: không có (team.py: CHG-002 planned 11/52, READY build). -->

# Phụ lục thiết kế 4 — CHG-002 (hẹp: T9 và T2)

Phạm vi: chỉ T9 (`review-09.md`, design-defect) và T2 (review vòng 1 của T2, design-defect, ghi ở `tasks.md:84`). Không phán T5, T21, T23, T31 (phụ lục 5 và `arch-ruling-2.md` lo các điểm đó). Không đổi AC, không đổi phạm vi "Giữ vành đai an toàn"; phụ lục này chỉ siết, không nới.

Tuân theo: ADR-040 QĐ 5 (`text_refusal` là định nghĩa duy nhất của "văn bản cho phép"), ADR-011 (một bộ phân giải đường dẫn: `source.resolve_safe_path`), ADR-022 QĐ 8 (test git dùng `GitSandbox`), design-addendum-2 L-1 (giữ nguyên; L-2 dưới đây bổ sung, không thay).

Nguồn đã đọc (không gọi Explore, theo lệnh của team-leader): `tasks.md:79-84`, `:124-129`; `review-09.md`; `design-addendum-2.md:71-86`; `design.md:80`, `:265-320`, `:699`, `:787`, `:805-815`; `git show` của `3a56462` (`change_guard.py:160-200`, `test_change_guard.py:196-250`, `test_propose_change.py:300-330`, `:405-450`, `test_apply_job.py:1-52`, `:1700-1785`, diff `a83923b..3a56462` của `test_propose_change.py`), `bad503a` (`test_utils.py:574-623`, `tests/test_test_utils.py:344-351`), `a6a6560` (`agent/tools/test_source.py:915-995`); `.team/profile.json` (`allowed_new_file_roots`, `protected_paths`).

---

## L-2. Luật chung: test lỗi cũ mà luật chặn của nó bị §3.2 gỡ

Dùng cho T9 và mọi task sau gỡ một luật chặn của §3.1/§3.2 hoặc bỏ một giới hạn cũ: T10..T14, T29 (bỏ ba giới hạn cũ), và task nào gặp ca tương tự.

**Khi nào là L-2, khi nào là L-1.**
- Cùng đầu vào **vẫn bị từ chối** ở cùng thời điểm (bởi luật sau của bộ chặn, hoặc bởi phép kiểm sau của tool/job) → đó là đổi giá trị ghim, theo **L-1** (addendum-2). Ví dụ: `a*.sh` từ "đuôi" sang `PATH_GIT_PATTERN`; `pkg/tool.sh` của `propose_edit` sang `propose_change.NOT_FOUND`.
- Cùng đầu vào nay **được nhận** (không còn lý do từ chối nào ở thời điểm đó, test sẽ thấy thành công, đề xuất được tạo, hoàn tác chạy xong) → **L-2**. Dev chọn đúng một trong ba cách, theo thứ tự ưu tiên:

**L-2a. Đổi đầu vào hoặc phần dựng (ưu tiên 1).** Dùng khi mục đích của test hoặc của dòng subTest (tên, chú thích, các assertion còn lại: "không tạo gì", "không ghi", trạng thái `Lỗi`) là một **đường lỗi vẫn còn** và luật bị gỡ chỉ là cái cò để đi vào đường đó. Đủ cả bốn điều kiện:
1. Đầu vào hoặc phần dựng mới bị một luật **còn trong §3.1/§3.2** từ chối, ở **cùng thời điểm** (đề xuất / áp dụng / hoàn tác) và qua **cùng hàm** như dòng cũ; ưu tiên cùng bước của `check_write_path` (bước kiểm đuôi cũ nằm ở bước 4, nên chọn `NAME_FORBIDDEN` hoặc `GIT_DIR`).
2. Lý do mới chưa có dòng nào trong cùng test (không đếm trùng; nếu mọi lý do còn lại đã có dòng thì dùng L-2c).
3. Phần dựng vá hằng đã bị gỡ (ví dụ `source.DUOI_CHO_PHEP`) thì đổi sang vá một hằng **còn sống của cùng module** (với `source`: `TEN_CAM`); không vá hàm của bộ chặn.
4. Lý do ghim lấy từ hằng (`change_guard.*`, `source.*`); mọi assertion khác giữ nguyên từng byte; giữ kiểu so (L-1 điểm 3).

**L-2b. Đổi thành test chấp nhận (ưu tiên 2).** Dùng khi mục đích của test là **chính luật bị gỡ** (tên hoặc chú thích nói "refuses <luật đó>") và không có test chấp nhận tương đương trong Expect của task. Giữ đầu vào; giá trị ghim mới là giá trị design cho (thường `None`); giữ kiểu so; **được đổi tên** sao cho tên nói đúng hành vi mới (STD-NAME-6). Nếu đã có test chấp nhận tương đương trong Expect → L-2c.

**L-2c. Bỏ (ưu tiên 3).** Chỉ khi sau L-2b, mọi dòng của test (hoặc dòng subTest) đã có dòng cùng đầu vào trong một test thuộc Expect của task, với assertion bằng hoặc chặt hơn. Dòng nào không có bản trùng thì **chuyển** sang test Expect hoặc test mới của task, giữ nguyên byte của dòng đó (chỉ giá trị đổi theo design). Không bao giờ bỏ dòng cuối cùng của một lý do lỗi còn trong §3.1; không bỏ test ghim AC trong §8.1.

**Ghi trong commit** (thân commit của task, mỗi test hoặc dòng subTest một dòng; cùng chỗ với các dòng `test-shape:` của L-1):
- `test-input: <file>::<Lớp>::<test>[<nhãn dòng>] — <đầu vào/phần dựng cũ> "<lý do cũ>" → <đầu vào/phần dựng mới> <lý do mới> — design §x.y (addendum-4 L-2a)`
- `test-accept: <file>::<Lớp>::<tên cũ> → <tên mới> — <giá trị cũ> → <giá trị mới> — design §x.y (addendum-4 L-2b)`
- `test-drop: <file>::<Lớp>::<test>[<dòng>] — phủ bởi <file>::<Lớp>::<test>[<dòng>]; chuyển <dòng> → <test đích> — design §x.y (addendum-4 L-2c)`

Dòng progress trong `tasks.md` ghi `L-1: <n>, L-2: <m>`. Reviewer đối chiếu từng dòng với L-2 và STD-TEST-5; một dòng không khớp là lỗi chặn merge (như L-1 điểm 5). Nhiều commit trong một task: **commit mới nhất** mang danh sách đầy đủ (kể cả các dòng đã có ở commit trước, đã sửa); reviewer chấm theo danh sách đó, không viết lại lịch sử.

**Test ngoài touchpoint.** L-1 điểm 4 áp nguyên cho L-2, với (a) đọc là "đỏ chỉ vì luật bị gỡ làm đầu vào thành hợp lệ"; dev chỉ được tự sửa không dừng theo **L-2a**; L-2b và L-2c ngoài touchpoint → `DESIGN_CONFLICT`.

- **Chọn:** ba cách có thứ tự, điều kiện đo được, dòng commit riêng cho từng cách.
- **Vì:** giữ được đường lỗi mà test cũ bảo vệ (lý do tồn tại của test), không âm thầm biến dòng từ chối thành dòng thành công (STD-TEST-5), và cho reviewer một phép đối chiếu máy móc như L-1.
- **Phương án khác:** (1) chỉ cho đổi giá trị (L-1 nguyên văn): biến dòng lỗi thành dòng thành công, xóa phép kiểm đường lỗi (review-09 blocker 2), bác; (2) luôn bỏ test lỗi cũ: mất đường lỗi lúc hoàn tác, bác; (3) để từng reviewer phán từng ca: không lặp lại được qua 7 task, bác.
- **Sai thì hoàn tác:** nếu một task sau có ca mà không cách nào trong ba đủ điều kiện → dev trả `DESIGN_CONFLICT` nêu tên test, designer phán riêng ca đó; L-2 không đổi cho các ca đã chấm.

---

## P-1. T9: áp L-2 và phán ba ghi chú của `review-09.md`

### P-1.1 Hai test của review-09 và hai test liên quan

| Test (trên `3a56462`) | Ca | Phán |
|---|---|---|
| `erp_ai/agent/tools/test_propose_change.py::TestProposeChange::test_new_file_errors_exists_and_no_parent` dòng `pkg/tool.exe` (`:430`) | Đầu vào nay hợp lệ, sẽ tạo đề xuất; mục đích là "lỗi tạo file không tạo gì" | **L-2a**: nhận nguyên cách đổi của dev `f"{APP}/pkg/.gitattributes"` → `change_guard.GIT_DIR` (cùng bước 4, cùng tool, lý do `GIT_DIR` chưa có dòng nào trong test này). Tên test giữ nguyên. |
| `erp_ai/agent/changes/test_apply_job.py::TestUndoCode::test_undo_rechecks_fail_without_writing[guard refusal]` (`:1734-1745`) | Phần dựng vá `source.DUOI_CHO_PHEP` mà bộ chặn không còn đọc; hoàn tác thành công | **L-2a**: phần dựng thành `patch.object(source, "TEN_CAM", re.compile(re.escape(os.path.basename(REL))))`; lý do ghim `change_guard.NAME_FORBIDDEN`. Đi qua `check_write_path`: `resolve_safe_path` từ chối, phân loại lại cho tới `source.text_refusal(rel)` → `TEXT_SECRET_NAME` (= `NAME_FORBIDDEN`), đúng bước 4, cùng lúc hoàn tác bước 2. Sống qua T49 (không dựa vào `DUOI_CHO_PHEP`). Chú thích của hàm `guard_refusal` đổi thành câu nói vá danh sách tên bí mật. |
| `erp_ai/agent/tools/test_change_guard.py::TestCheckWritePath::test_refuses_extension_outside_read_list_even_for_new_file` (`:206`) | Mục đích là chính luật đuôi; mọi dòng nay `None` (deferred 1) | **L-2c bỏ test**: 5 dòng `run.sh`(False), `new.sh`, `lib.so`, `Makefile`, `conf/settings` đã có cùng đầu vào trong Expect `TestCheckWritePath::test_any_text_extension_allowed` với assertion chặt hơn (`GuardResult` đủ trường). **Chuyển** dòng `("myapp", True)` sang test mới `test_app_dir_itself_path_invalid` với giá trị mới `PATH_INVALID` (P-1.2 ghi chú 2). **Chuyển** nguyên byte hai dòng symlink (`os.symlink(… "run.sh" …, … "sh_link.py")` và `self.assertEqual(self.reason("myapp/sh_link.py"), None)`) xuống cuối `test_any_text_extension_allowed` (test đó đã ghi `myapp/run.sh`). T10 lật dòng này sang `PATH_SYMLINK` theo L-1. |
| `erp_ai/agent/tools/test_propose_change.py::TestProposeChange::test_each_guard_refusal_creates_zero_proposals` dòng `pkg/tool.sh` (`:317`) | Cùng đầu vào vẫn bị từ chối (tool: file không tồn tại) | **L-1, giữ dòng** (deferred 2: không bỏ; dòng này là bằng chứng ở mức tool rằng đuôi lạ đi tới phép kiểm tồn tại). Giá trị đổi sang hằng `propose_change.NOT_FOUND` (deferred 3, L-1 điểm 3 "lấy từ hằng"). |

### P-1.2 Ba ghi chú thiết kế

**Ghi chú 1 — thứ tự trong bước 4.** Xác nhận thứ tự của mã: `license.txt` → `source.text_refusal(rel)` (tên bí mật → `.git*`). `design.md:287` liệt kê tập luật của bước 4, không phải thứ tự; phụ lục này chốt thứ tự trên. `myapp/.github/license.txt` → `NAME_FORBIDDEN`.
- **Vì:** cả `license.txt` và tên bí mật đều cho `NAME_FORBIDDEN`, nên thứ tự chỉ quyết định ca giao với `.git*`, và "tên trước git" khớp AC-51 cùng thứ tự trong `text_refusal`.
- **Phương án khác:** `text_refusal` trước `license.txt` → `.github/license.txt` ra `GIT_DIR`, ngược "tên trước git"; bác.
- **Sai thì hoàn tác:** nếu `BB::TestRingMatrix` (T44) cần `GIT_DIR` cho ca giao → đổi hai dòng `if` trong `check_write_path` và một giá trị ghim; không đổi gì khác.

**Ghi chú 2 — chính thư mục app làm đích.** Chốt: đích có đúng một thành phần sau `apps/` (chính thư mục app, `"myapp"`, `"myapp/"`, `"myapp/."`) → `PATH_INVALID`. Đặt cùng chỗ với luật "thư mục app không có" (sau `APP_NOT_ALLOWED`, trước `APP_FORBIDDEN`): `if len(parts) == 1 or not os.path.isdir(os.path.join(root, parts[0])): return _refused(PATH_INVALID)`; docstring bước 2 thêm "the app folder itself".
- **Vì:** trước T9 chỉ luật đuôi chặn ca này; T9 gỡ luật đuôi nên chính T9 phải đóng lại lỗ (L-1 điểm 1 cùng tinh thần: sửa ở task gây ra). Đích là thư mục không phải file văn bản nào; chặn ở bộ chặn là chặt hơn, không nới vành đai. `new_dirs` của `check_block` luôn nằm dưới thư mục app (thư mục app phải tồn tại), nên luật này không đụng `check_block`. Không thêm bộ phân giải mới (ADR-011): dùng `parts` đã có.
- **Phương án khác:** để các phép kiểm sau (tạo "đã tồn tại", xóa/đổi tên `NOT_REGULAR_FILE`, `write_atomic`) tự từ chối: chưa ai đọc chắc cả hai thời điểm (review-09 "Không kiểm được"), lỗi đến muộn và lý do khác nhau theo loại mục; bác.
- **Sai thì hoàn tác:** nếu lần chạy cả app đỏ ở một test ngoài touchpoint ghim `reason=None` cho chính thư mục app → bỏ phần `len(parts) == 1 or`, dời luật sang `check_block` bước 2 (hình dạng) ở T12, báo designer.

**Ghi chú 3 — chỗ của luật "thư mục app không có".** Xác nhận chỗ của mã: sau `APP_NOT_ALLOWED`, trước `APP_FORBIDDEN`. `("a", "app không có trong danh sách được sửa")` của `PC` giữ nguyên; `erp_ai` có trong danh sách mà không có thư mục → `PATH_INVALID` (vẫn bị từ chối; thư mục `erp_ai` thật luôn có).
- **Vì:** "app không được phép" là câu đúng và hữu ích hơn cho app không có trong danh sách, dù thư mục có hay không.
- **Phương án khác:** kiểm thư mục trước `APP_NOT_ALLOWED` → dòng `"a"` lật sang `PATH_INVALID`, phải sửa test ghim §3.1 không vì lý do nào; bác.
- **Sai thì hoàn tác:** đổi thứ tự hai dòng `if`, sửa một giá trị ghim theo L-1.

### Việc dev phải sửa trên 3a56462
Nhánh `team/CHG-002-task-9`, một commit mới trên `3a56462` (không viết lại lịch sử, không force-push):
1. `erp_ai/agent/tools/test_change_guard.py`: thêm `TestCheckWritePath::test_app_dir_itself_path_invalid` (đỏ trước): `"myapp"`, `"myapp/"`, `"myapp/."` với `new_file` True và False → `change_guard.PATH_INVALID`; `"helpdesk"` (không trong `ALLOWED`) → `change_guard.APP_NOT_ALLOWED` (ghim thứ tự ghi chú 3). Dán dòng đỏ (`None != 'đường dẫn không hợp lệ hoặc nằm ngoài apps/'`).
2. `erp_ai/agent/tools/change_guard.py`: luật ghi chú 2 (một điều kiện thêm vào dòng `if` kiểm thư mục app) và một câu trong docstring.
3. `test_change_guard.py`: xóa `test_refuses_extension_outside_read_list_even_for_new_file`; chuyển hai dòng symlink xuống cuối `test_any_text_extension_allowed` (P-1.1).
4. `erp_ai/agent/tools/test_propose_change.py`: giữ dòng `:430` của dev; dòng `:317` đổi `"file không tồn tại"` → `propose_change.NOT_FOUND`.
5. `erp_ai/agent/changes/test_apply_job.py` (file thêm vào touchpoint): `import re` đúng thứ tự abc (sau `import os`); phần dựng `guard_refusal` và lý do ghim theo P-1.1; chú thích một dòng.
6. Chạy `cmd.test_one` với `test_change_guard.py`, `test_propose_change.py`, `test_apply_job.py`, `erp_ai/tests/test_architecture.py`; dán `Ran … / OK` của từng file.
7. Thân commit mang danh sách đầy đủ (thay các dòng của `da795ea` và `3a56462`; deferred 4):
   - `test-shape:` (L-1, 4 dòng): `test_change_guard.py::…::test_refusal_wording_matches_design_table`, `…::test_double_refusal_returns_earlier_reason_of_table_order`, `…::TestCheckWritePathGit::test_refuses_git_pattern_names` (chữ như đã sửa ở `3a56462`), `test_propose_change.py::TestProposeChange::test_each_guard_refusal_creates_zero_proposals` (`pkg/tool.sh` "đuôi file không được phép" → `propose_change.NOT_FOUND`; `.git/notes.md` "không được chạm thư mục .git" → `change_guard.GIT_DIR`).
   - `test-input: erp_ai/agent/tools/test_propose_change.py::TestProposeChange::test_new_file_errors_exists_and_no_parent[pkg/tool.exe] — pkg/tool.exe "đuôi file không được phép" → pkg/.gitattributes change_guard.GIT_DIR — design §3.2 bước 4 (addendum-4 L-2a)`
   - `test-input: erp_ai/agent/changes/test_apply_job.py::TestUndoCode::test_undo_rechecks_fail_without_writing[guard refusal] — patch source.DUOI_CHO_PHEP={".txt"} "đuôi file không được phép" → patch source.TEN_CAM=re.compile(re.escape("mod.py")) change_guard.NAME_FORBIDDEN — design §3.2 bước 4 (addendum-4 L-2a)`
   - `test-drop: erp_ai/agent/tools/test_change_guard.py::TestCheckWritePath::test_refuses_extension_outside_read_list_even_for_new_file — phủ bởi TestCheckWritePath::test_any_text_extension_allowed[run.sh,new.sh,lib.so,Makefile,conf/settings]; chuyển [myapp] → test_app_dir_itself_path_invalid (PATH_INVALID), [sh_link.py] → test_any_text_extension_allowed — design §3.2 (addendum-4 L-2c, P-1.2 ghi chú 2)`
   - Progress: `L-1: 4, L-2: 3`.

---

## P-2. T2: đo NFR-14 cho repo `erp_ai` để test lặp lại được

**Chọn: so "phần mã" của repo `erp_ai` thật, bỏ các đường dẫn phiên.** Bốn repo lõi giữ nguyên (HEAD, `status --porcelain`). Với `erp_ai`:
- Hằng `ERP_AI_SESSION_PATHS = ("docs", ".team", ".claude")` trong `erp_ai/test_utils.py`: các đường dẫn cấp gốc mà phiên khác ghi và commit ở cây chính (tài liệu `docs/team/**`, `.team/current.json`, `.team/miyano-site.lock`, `.claude/agent-memory/`).
- Hàm `erp_ai_code_state(repo: str) -> tuple[str, str]`, chỉ git đọc, cùng `env`, `stdin`, `timeout`, cùng cách báo lỗi như vòng lặp hiện có (tách vòng gọi git hiện có thành một hàm dùng chung, STD-DESIGN-4):
  1. `["git", "-C", repo, "--no-optional-locks", "ls-tree", "HEAD"]`, rồi bỏ các dòng có tên (phần sau tab) nằm trong `ERP_AI_SESSION_PATHS` → phần tử 0 (danh sách cây cấp gốc của phần mã, không phải sha HEAD).
  2. `["git", "-C", repo, "--no-optional-locks", "status", "--porcelain", "--", ".", ":(exclude)docs", ":(exclude).team", ":(exclude).claude"]` → phần tử 1.
- `real_core_repos_snapshot()` = 4 repo lõi như cũ, cộng khóa `erp_ai` = `erp_ai_code_state(<bench>/apps/erp_ai)`. Thứ tự lời gọi: 8 lời gọi cũ, rồi `ls-tree`, rồi `status` của `erp_ai` (10 lời gọi).
- `RealCoreReposUntouchedMixin` không đổi logic; docstring thêm NFR-14 và câu "erp_ai: phần mã, bỏ `ERP_AI_SESSION_PATHS`".
- Phần qa đo tay (§8.1 NFR-14) giữ: qa lấy `real_core_repos_snapshot()` trước và sau `cmd.test` (5 khóa), dán cả hai; **thêm** HEAD và `status --porcelain` đầy đủ của `erp_ai` trước/sau, mỗi thay đổi trong `ERP_AI_SESSION_PATHS` phải khớp một dòng journal của một phiên khác; thay đổi không giải thích được → NFR-14 trượt.

- **Vì:** commit tài liệu của phiên khác đổi HEAD nhưng không đổi cây cấp gốc ngoài `docs`/`.team`/`.claude`, nên test 6 lớp đang dùng mixin (và AB, BB sau này) xanh lặp lại được (STD-TEST-6), mà vẫn bắt được mọi ghi/commit lạc vào mã, `README.md`, `pyproject.toml`… của `erp_ai` thật, là chỗ một sandbox `erp_ai` (có `README.md`, `pkg/…`) sẽ lạc tới. Phần bỏ sót (lạc vào `docs/`) do qa đo tay phủ.
- **Phương án khác:** (1) chỉ so thư mục gói `erp_ai/erp_ai/`: bỏ sót ghi lạc ở gốc repo (`README.md` của sandbox), bác; (2) chỉ để qa đo tay: mất phép kiểm theo từng lớp chỉ ra lớp gây lỗi, và R-11 đã hứa phép kiểm tự động, bác; (3) giữ HEAD đầy đủ và cấm commit tài liệu khi đang chạy test: không ép được giữa các phiên, bác; (4) băm danh sách cây thành 40 hex để giữ hình dạng cũ: mất thông tin chẩn đoán trong câu lỗi của mixin, không cần, bác.
- **Sai thì hoàn tác:** nếu mixin vẫn đỏ ở lần chạy không ai đụng mã (ví dụ có đường dẫn phiên khác ngoài ba tên trên) → thêm đúng tên đó vào `ERP_AI_SESSION_PATHS`, ghi một dòng journal; nếu vẫn không lặp lại được sau một lần thêm → bỏ khóa `erp_ai` khỏi mixin, NFR-14 chỉ còn qa đo tay (phương án 2), báo designer sửa R-11. Đỏ vì một phiên khác commit **mã** vào nhánh đang checkout ở cây chính trong lúc chạy là nhiễu thật, không phải test chập chờn: chạy lại trong một lần giữ khóa site, không ghi `debt.md`.

**Ba test ghim 4 repo / 8 lời gọi ở `erp_ai/agent/tools/test_source.py`: sửa ở T2.** Theo L-1 điểm 1 (sửa ở task làm đổi hình dạng). Phụ lục này thêm vào danh sách "hình dạng" của L-1 điểm 2: "khóa và lời gọi git của `real_core_repos_snapshot` (R-11, addendum-4 P-2)".
- **Vì:** chính diff của T2 làm ba test đỏ; dời sang task khác thì T2 merge khi đỏ (STD-CI-2).
- **Phương án khác:** sửa ở T22/T44 (người dùng mixin đầu tiên của AB/BB): T2 không merge được, bác.
- **Sai thì hoàn tác:** không áp dụng (chỉ là vị trí sửa).

### Việc dev phải sửa trên bad503a
Nhánh `team/CHG-002-task-2`, một commit mới trên `bad503a`:
1. `erp_ai/tests/test_test_utils.py`: thêm `TestRealCoreRepos::test_erp_ai_code_state_ignores_session_paths_only` (đỏ trước: `AttributeError … 'erp_ai_code_state'`) trên `GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)`, gọi `erp_ai_code_state(sandbox.repo("custom_app"))`: commit `docs/team/x.md`, ghi chưa theo dõi `.team/miyano-site.lock` và `.claude/m.md`, sửa chưa commit `docs/team/x.md` → trạng thái **bằng** trạng thái đầu; ghi chưa theo dõi `README2.md` → phần tử 1 khác; commit `pkg/x.py` → phần tử 0 khác. Sửa `TestRealCoreRepos::test_snapshot_includes_erp_ai`: giữ `set(snapshot) == {*CORE_APPS, "erp_ai"}`; thay so `head == rev-parse HEAD` bằng `snapshot["erp_ai"] == erp_ai_code_state(<bench>/apps/erp_ai)`.
2. `erp_ai/test_utils.py`: `ERP_AI_SESSION_PATHS`, `erp_ai_code_state`, hàm gọi git dùng chung, `real_core_repos_snapshot` như trên; docstring mixin.
3. `erp_ai/agent/tools/test_source.py` (file thêm vào touchpoint), lớp `TestRealCoreReposUntouchedMixin`, theo L-1:
   - `test_real_core_repos_snapshot_reads_the_four_core_repos` (`a6a6560:…:930`): danh sách khóa 4 → `["erp_ai", "erpnext", "frappe", "helpdesk", "hrms"]`; vòng regex 40 hex lặp trên 4 repo lõi (`("frappe", "erpnext", "helpdesk", "hrms")`), không trên `snapshot.items()`. Tên giữ nguyên (vẫn đúng: nó đọc 4 repo lõi).
   - `test_real_core_repos_snapshot_runs_only_read_commands` (`:947-951`): danh sách `expected` thêm đúng hai argv của `erp_ai` (bước 1, 2 ở trên) sau 8 argv cũ; so bằng đủ danh sách; ba assertion `kwargs` áp cho cả 10 lời gọi; `snapshot["hrms"]` giữ nguyên.
   - `test_real_core_repos_mixin_on_real_repos_passes_when_untouched` (`:984`): danh sách khóa 4 → 5 như trên.
   - `test_real_core_repos_mixin_detects_change` không đỏ (vá cả hai ảnh chụp, 4 khóa): không sửa.
4. Chạy `cmd.test_one` với `erp_ai/tests/test_test_utils.py`, `erp_ai/agent/tools/test_source.py`, `erp_ai/agent/changes/test_apply_job.py` (lớp `TestCommitCrossChecks` dùng mixin); dán `Ran … / OK`.
5. Thân commit: 3 dòng `test-shape: erp_ai/agent/tools/test_source.py::TestRealCoreReposUntouchedMixin::<test> — <4 repo / 8 lời gọi> → <4 repo + erp_ai / 10 lời gọi> — design R-11 (addendum-4 P-2)`. Progress: `L-1: 3`.

---

## tasks.md đổi gì (tech-lead sửa; designer không sửa tasks.md)

| Task | Touchpoint thêm | Returns / Expect đổi | Tên test thêm hoặc đổi |
|---|---|---|---|
| T9 | `erp_ai/agent/changes/test_apply_job.py` | Returns thêm: "đích là chính thư mục app → `PATH_INVALID`, cùng dòng với luật thư mục app không có (addendum-4 P-1.2)"; "test lỗi cũ theo addendum-4 L-2 (P-1.1)"; câu "`test_propose_change.py`: chỉ sửa test ghim 8 đuôi" thành "sửa theo L-1/L-2 (P-1.1)". Expect thêm `test_one` với `test_apply_job.py` xanh | thêm `TestCheckWritePath::test_app_dir_itself_path_invalid`; bỏ `TestCheckWritePath::test_refuses_extension_outside_read_list_even_for_new_file` (L-2c) |
| T10 | — | Ghi chú: dòng `myapp/sh_link.py` nay ở cuối `test_any_text_extension_allowed`; bước 6 lật nó sang `PATH_SYMLINK` theo L-1; L-2 áp cho test lỗi cũ | — |
| T11..T14, T29 | — | Thêm một dòng "test lỗi cũ có đầu vào thành hợp lệ: addendum-4 L-2" | — |
| T2 | `erp_ai/agent/tools/test_source.py` | Returns: `real_core_repos_snapshot()` thêm khóa `erp_ai` = `erp_ai_code_state(...)` (phần mã: `ls-tree HEAD` và `status --porcelain` bỏ `ERP_AI_SESSION_PATHS`), không phải HEAD; thêm `ERP_AI_SESSION_PATHS`, `erp_ai_code_state(repo)`. Expect thêm test mới và `test_one` với `test_source.py` xanh | thêm `TestRealCoreRepos::test_erp_ai_code_state_ignores_session_paths_only`; sửa `TestRealCoreRepos::test_snapshot_includes_erp_ai`; 3 test `TestRealCoreReposUntouchedMixin::*` ở `test_source.py` (L-1) |
| T22, T32, T33, T44 | — | không đổi (bỏ chặn khi T2 merge) | — |

## design.md đọc theo phụ lục này (không sửa design.md)
- R-11 (`design.md:80`): "Thêm `erp_ai` vào `RealCoreReposUntouchedMixin`" đọc là "thêm **phần mã** của `erp_ai` (addendum-4 P-2)".
- §3.2 `check_write_path` bước 2: thêm "đích là chính thư mục app, hoặc thư mục app không có → `PATH_INVALID`" (đặt sau `APP_NOT_ALLOWED`); bước 4: thứ tự `license.txt` → `text_refusal` (tên bí mật → `.git*`).
- §8.1 NFR-14 (`design.md:787`): như P-2 (mixin so phần mã của `erp_ai`; qa so 5 khóa và đối chiếu thay đổi đường dẫn phiên với journal).
- §8.3 "Test cũ phải sửa" thêm: "test lỗi cũ có đầu vào thành hợp lệ khi §3.2 gỡ luật → addendum-4 L-2 (T9: `PC::…::test_new_file_errors_exists_and_no_parent`, `AB::TestUndoCode::test_undo_rechecks_fail_without_writing`, `CG::…::test_refuses_extension_outside_read_list_even_for_new_file`); ba test ghim 4 repo ở `test_source.py` (T2)".

## Assumptions decided by the team
- A4-1: ba tên `docs`, `.team`, `.claude` là đủ các đường dẫn phiên ở cây chính hôm nay (theo `git status` đầu phiên: chỉ thấy thay đổi dưới ba tên này). Sai → P-2 "Sai thì hoàn tác".
- A4-2: lúc hoàn tác, bước 2 kiểm lại đi qua `change_guard.check_write_path` (như phần dựng cũ vá `source.DUOI_CHO_PHEP` cho thấy). Sai (lý do khác `NAME_FORBIDDEN`) → vá `change_guard.PROTECTED_FILE_NAME = "mod.py"` thay cho `TEN_CAM` (cùng bước 4, cùng lý do), dòng `test-input:` ghi phần dựng đó.

Câu hỏi nghiệp vụ: 0.

## Kiểm tra
**Touchpoint so với `allowed_new_file_roots` và `protected_paths`** (`.team/profile.json`: roots `['erp_ai', 'docs', '.github']`; protected `['.env', '.env.*', '**/*.pem', '**/*.key', 'license.txt']`):

| Đường dẫn | Mới/sửa | Root | Khớp protected |
|---|---|---|---|
| `docs/team/features/CHG-002/design-addendum-4.md` | mới | `docs` | không |
| `erp_ai/agent/tools/change_guard.py` | sửa | `erp_ai` | không |
| `erp_ai/agent/tools/test_change_guard.py` | sửa | `erp_ai` | không |
| `erp_ai/agent/tools/test_propose_change.py` | sửa | `erp_ai` | không |
| `erp_ai/agent/changes/test_apply_job.py` | sửa | `erp_ai` | không |
| `erp_ai/test_utils.py` | sửa | `erp_ai` | không |
| `erp_ai/tests/test_test_utils.py` | sửa | `erp_ai` | không |
| `erp_ai/agent/tools/test_source.py` | sửa | `erp_ai` | không |

Không có file mã mới. Chuỗi `license.txt` chỉ là giá trị trong test, không phải file bị chạm.

**AC và NFR.** Spec và test plan (`design.md` §8.1, dòng `test plan:`): `AC-36 AC-37 AC-38 AC-39 AC-40 AC-41 AC-42 AC-43 AC-44 AC-45 AC-46 AC-47 AC-48 AC-49 AC-50 AC-51 AC-52 AC-53 AC-54 AC-55 AC-56 AC-57 | NFR-12 NFR-13 NFR-14 NFR-15`. Phụ lục này không bỏ test nào có tên trong §8.1 (`git grep` trong `design.md` và các phụ lục: bốn test cũ ở P-1.1 không phải dòng test của AC nào); NFR-14 giữ cả phần tự động (mixin, nay lặp lại được) và phần tay. Còn **22/22 AC, 4/4 NFR** có test.
