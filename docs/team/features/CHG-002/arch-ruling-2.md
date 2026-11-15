Feature: CHG-002
Stage: architect
Author-agent: architect
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Phán quyết kiến trúc 2: hai xung đột ADR của build lượt 2 (T5, T23)

Đầu vào đã đọc (2026-11-15, chỉ đọc):
- `tasks.md:100-104` (T5), `:106-109` (T6), `:215-220` (T23); `review-05.md`.
- `e5f7109:erp_ai/agent/changes/file_writer.py` (`_refuse_unsafe_path` dòng 24-35, `make_parents` 38-66, `remove_empty_dirs` 69-83).
- `ad729a7:erp_ai/agent/changes/restart_check.py` (dòng 12-13 `import psutil`, `import redis`; chỉ dùng `psutil.Process`, `psutil.Error`, `redis.exceptions.RedisError`).
- `a6a6560:erp_ai/tests/test_architecture.py`: `SAFE_PATH_NAME = "safe_path"` (dòng 1899, so **chuỗi con** trong tên hàm), `ROOT_CHECK_CALLS` (1900), `ROOT_CHECK_ALLOWLIST` (1904-1912), `check_change_guard_uses_resolve_safe_path` (2117-2171, lỗi ở 2160-2161), test 4667; `ALLOWED_TOP_LEVEL_MODULES` (160), `check_import_boundaries` (537-550), `test_layer_imports` (4372-4382), mẫu ca tự kiểm `test_import_boundaries_catch_anthropic_and_other_apps` (5499).
- `team/CHG-002:erp_ai/agent/tools/source.py:124-165`: `get_source_root()` trả `realpath`; `resolve_safe_path(rel)` trả `realpath(root/rel)` khi nằm trong gốc và `text_refusal(rel)` là `None` (luật `TEN_CAM` và luật thành phần `.git*`), ngược lại `None`.
- `design-addendum-1.md:145-183` (A-3), `:200-218` (A-6); `design.md:559-581` (§4.4 bước 5).
- ADR-001 Ràng buộc dòng cuối ("chỉ import mã của `frappe`, `helpdesk` và thư viện khai trong `pyproject.toml`"); ADR-011 Ràng buộc ("Bộ chặn đường dẫn ghi gọi `resolve_safe_path`; không có hàm khử symlink/kiểm gốc thứ hai trong `erp_ai/**`"); ADR-040 Quyết định 4 (gạch cuối) và Ràng buộc ("`file_writer` từ chối mọi thành phần `.git*` và mọi symlink trên đường dẫn ghi, xóa và tạo thư mục").
- `pyproject.toml:10-13` (chỉ khai `anthropic`); `apps/frappe/pyproject.toml:61` `psutil~=5.9.5`, `:69` `redis~=4.5.5`.

Không gọi Explore (lệnh của team-leader: đọc đúng các chỗ trên).

Cả hai phán quyết là quyết định kiến trúc (đổi cách hiểu một dòng Ràng buộc của ADR cũ), nên được ghi thành **Phán quyết C-2** và **Phán quyết C-3** ở cuối `docs/team/adr/ADR-040.md`. Thân ADR-001 và ADR-011 không sửa.

---

## Phán quyết 1 (T5) = ADR-040 Phán quyết C-2

### Nguyên nhân thật
Luật bắt tên vì `"safe_path"` là chuỗi con của `_refuse_unsafe_path`. Nhưng đổi tên thôi thì chưa đủ: thân hàm ở `e5f7109` tự tính "trong gốc" bằng `relpath` với `realpath(get_source_root())` và tự so `realpath(parent) != parent`. Đó đúng là "kiểm gốc thứ hai, khử symlink thứ hai" mà ADR-011 cấm. Luật `_root_check_calls` chỉ không thấy vì nó chỉ dò `commonpath`/`is_relative_to`. Cả ADR-040 (file_writer phải kiểm lại) lẫn ADR-011 (chỉ một bộ phân giải) đều đúng; chỗ sai là cách A-3.1 viết phép kiểm lại.

### Chọn
**Gọi lại hàm đã có.** Phép kiểm lại của `file_writer` là một câu hỏi đặt cho bộ phân giải duy nhất: "bộ phân giải có chấp nhận đường dẫn này **và** không đổi nó đi chút nào không?".

Hàm mới trong `erp_ai/agent/changes/file_writer.py`, thay `_refuse_unsafe_path` ở mọi chỗ gọi:

`_refuse_unless_canonical(full_path) -> None`
- `full = os.path.abspath(full_path)`; `rel = os.path.relpath(full, source.get_source_root())`.
- Ném `ValueError` khi `source.resolve_safe_path(rel) != full`. Không ném thì trả `None`.
- Một câu lỗi duy nhất, ví dụ `"file_writer does not touch this path (outside the apps root, .git*, secret name or symlink)"`. Không phân loại lý do (phân loại là việc của `check_write_path`; phân loại ở đây lại thành phép kiểm thứ hai). Test chỉ khẳng định `ValueError` và hệ quả trên đĩa, không so câu chữ.
- Trong hàm không có `realpath`, `commonpath`, `is_relative_to`, không có luật `.git*` riêng.

Hàm này phủ đủ ba điều của F-3 và chặt hơn, không lỏng hơn:

| Trường hợp | Vì sao bị từ chối |
|---|---|
| ngoài gốc `apps/` (kể cả chính gốc) | `resolve_safe_path` trả `None` (`_inside` sai) |
| một thành phần bắt đầu bằng `.git` | `text_refusal` trả `GIT_DIR` → `None` |
| tên khớp `TEN_CAM` (mới, chặt hơn F-3) | `text_refusal` trả `TEXT_SECRET_NAME` → `None` |
| một thư mục cha bất kỳ từ gốc tới đích là symlink | `realpath` khác `abspath` |
| chính thành phần cuối là symlink (mới, chặt hơn F-3) | `realpath` khác `abspath` |

Mọi đường dẫn hợp lệ đã qua `check_write_path`, vốn dựng trên `resolve_safe_path` và cũng chặn `TEN_CAM`, nên phần chặt hơn không từ chối đường dẫn hợp lệ nào (kể cả đề xuất tạo trước CHG-002).

Hợp đồng mới của hai hàm T5 (thay "Returns (A-3.1)" của T5):
- `make_parents(full_path, app_dir) -> list[str]`: giữ chữ ký, giữ kiểm `isdir(app)` / `islink(app)` và kiểm "file nằm ngoài `app_dir`" (xem dưới). Với mỗi tầng chưa có, từ trên xuống: `_refuse_unless_canonical(current)` **trước** `os.mkdir` (không tạo gì qua một tổ tiên là symlink hay dưới `.git*`; trả lời câu hỏi thiết kế của reviewer ở `review-05.md` "Không kiểm được từ diff"), rồi `os.mkdir(current, NEW_DIR_MODE)`, ghi vào `created`, rồi `_refuse_unless_canonical(current)` lần nữa cộng `os.path.islink(current)` (thư mục bị tráo sau `mkdir`, ADR-040 Quyết định 4 gạch cuối). Sai ở bất kỳ phép kiểm nào: trả lại phần đã tạo như ở `e5f7109` (`unlink` cho symlink, `rmdir` cho thư mục) rồi ném lại `ValueError`. Tầng đã có (`lexists`) không kiểm riêng: phép kiểm trước `mkdir` của tầng đầu tiên được tạo phủ mọi tổ tiên, và khi không tạo tầng nào thì `write_atomic` kiểm (T6).
- `remove_empty_dirs(dirs) -> list[str]`: từ sâu nhất lên; **bỏ qua** (không lỗi, không có trong kết quả) khi `os.path.islink(d)`, hoặc `_refuse_unless_canonical(d)` ném `ValueError`, hoặc không phải thư mục, hoặc không rỗng; còn lại `os.rmdir(d)`. Bỏ phép so `os.path.realpath(d) != os.path.abspath(d)` (đã nằm trong `_refuse_unless_canonical`; `file_writer.py` không còn gọi `realpath`).
- Kiểm "file nằm ngoài `app_dir`" của `make_parents` (`relpath(parent, app)` bắt đầu bằng `..`) **không** phải kiểm gốc theo nghĩa ADR-011: nó chỉ tính dải thư mục cần tạo và chỉ từ chối; quyết định an toàn vẫn là `check_write_path` cộng `_refuse_unless_canonical`. Được giữ, không cần ngoại lệ.

### Luật kiến trúc
- Luật cũ **không đổi**: `SAFE_PATH_NAME`, `ROOT_CHECK_CALLS`, `ROOT_CHECK_ALLOWLIST`, `check_change_guard_uses_resolve_safe_path` giữ nguyên từng dòng. Tên mới không chứa `safe_path`, thân mới không gọi `commonpath`/`is_relative_to`, nên `test_change_guard_uses_resolve_safe_path` xanh mà không cần ngoại lệ.
- Luật **thêm** (ADR-040 C-2) trong `erp_ai/tests/test_architecture.py`, cạnh `check_fs_writes_only_in_file_writer`:
  `check_file_writer_rechecks_through_resolver(sources) -> list`, vi phạm khi:
  1. `agent/changes/file_writer.py` không có hàm cấp module `_refuse_unless_canonical`, hoặc hàm đó không gọi `erp_ai.agent.tools.source.resolve_safe_path` (giải tên qua `import_aliases`/`resolved_name` như `SAFE_PATH_CALL`);
  2. `file_writer.py` có lời gọi `realpath`, `commonpath`, `is_relative_to` hoặc `readlink` ở bất kỳ đâu (bộ khử symlink/kiểm gốc thứ hai);
  3. một hàm trong hằng tay `FILE_WRITER_RECHECKERS` không gọi `_refuse_unless_canonical`. T5: `("make_parents", "remove_empty_dirs")`; T6 thêm `"write_atomic"`, `"remove_file"`.
- Ca tự kiểm của luật (cùng kiểu `assertCaught` ở dòng 5499):
  - `test_file_writer_rechecks_through_resolver`: trên mã thật → `[]`; và `self.assertIn("def _refuse_unless_canonical(", self.sources[FILE_WRITER_FILE])` để quét không mù.
  - `test_file_writer_recheck_rule_catches_bypass`, nguồn tổng hợp cho `agent/changes/file_writer.py`:
    - `_refuse_unless_canonical` có thân `pass` → bắt (thiếu lời gọi bộ phân giải);
    - có lời gọi `os.path.realpath(x)` trong `remove_empty_dirs` → bắt;
    - `from os.path import realpath as rp` rồi `rp(x)` → bắt;
    - `make_parents` không gọi `_refuse_unless_canonical` → bắt;
    - một hàm `_refuse_unsafe_path` trong file này → `check_change_guard_uses_resolve_safe_path` vẫn bắt "second path resolver" (luật tên không bị nới).

### Dev phải sửa trên `e5f7109` (nhánh `team/CHG-002-task-5`)
1. `file_writer.py`: đổi `_refuse_unsafe_path` thành `_refuse_unless_canonical` với thân ở trên; `make_parents` thêm phép kiểm trước `mkdir`; `remove_empty_dirs` bỏ phép so `realpath`. `_refuse_git_dir`, `write_atomic`, `remove_created` chưa đụng (T6).
2. `test_file_writer.py`: 21 test hiện có giữ, sửa tên hàm nếu có test gọi thẳng. Thêm:
   - `TestMakeParents::test_symlinked_ancestor_refused_before_mkdir` (tầng một có sẵn là symlink ra `self.apps.outside`; spy `file_writer.os.mkdir` → 0 lời gọi, `ValueError`, `outside` không đổi);
   - `TestRefuseUnlessCanonical::test_plain_path_accepted` và `test_outside_git_secret_and_symlinked_target_refused` (một ca cho mỗi dòng của bảng trên).
3. `erp_ai/tests/test_architecture.py`: thêm luật và hai ca tự kiểm ở trên.
4. Chạy `test_one` cho `test_file_writer.py` **và** module `erp_ai.tests.test_architecture` (theo lock site chung) trước khi báo DONE.

Đây là đổi do phán quyết, không phải vòng sửa của review; tech-lead quyết có tính vào `max_rework` hay không.

### Task đổi trong `tasks.md` (tech-lead sửa, architect không sửa file đó)
- **T5**: touchpoint thêm `erp_ai/tests/test_architecture.py`. Returns: `_refuse_unless_canonical(full_path) -> None` thay `_refuse_unsafe_path` với hợp đồng trên; `make_parents` kiểm trước và sau `mkdir`; `remove_empty_dirs` bỏ phép so `realpath`. Expect thêm `TestMakeParents::test_symlinked_ancestor_refused_before_mkdir`, `TestRefuseUnlessCanonical::test_plain_path_accepted`, `test_outside_git_secret_and_symlinked_target_refused`, `ARCH::TestArchitecture::test_change_guard_uses_resolve_safe_path`, `test_file_writer_rechecks_through_resolver`, `test_file_writer_recheck_rule_catches_bypass` xanh.
- **T6**: Receives `_refuse_unless_canonical` (T5) thay `_refuse_unsafe_path`; Returns: `write_atomic` và `remove_file` gọi `_refuse_unless_canonical(full)` ở chỗ A-3.1 ghi `_refuse_unsafe_path(full)`, thứ tự kiểm của `remove_file` giữ nguyên; touchpoint thêm `erp_ai/tests/test_architecture.py` (thêm `"write_atomic"`, `"remove_file"` vào `FILE_WRITER_RECHECKERS`); Expect thêm `ARCH::TestArchitecture::test_file_writer_rechecks_through_resolver` xanh.
- T7, T8, T47, T48: không đổi chữ (không nhắc tên hàm); chỉ hết bị chặn khi T5 tick.
- `design-addendum-1.md` A-3.1 và A-3.2: designer cập nhật tên hàm và bảng hợp đồng theo phán quyết này ở addendum kế tiếp (architect không sửa design).

### Phương án khác
- **Chỉ đổi tên** (ví dụ `_refuse_risky_target`), giữ thân `relpath`/`realpath`: lọt luật tên nhưng vẫn là bộ kiểm gốc và khử symlink thứ hai, chỉ là luật dò chưa thấy. Hai luật cùng một việc sẽ lệch nhau ở lần sửa sau (đúng rủi ro ADR-011 nêu). Không chọn.
- **Ngoại lệ có tên trong luật** (`("agent/changes/file_writer.py", "_refuse_unsafe_path")` vào `ROOT_CHECK_ALLOWLIST`, bỏ qua tên): hợp thức hóa bộ phân giải thứ hai; luật `.git*` có hai bản (`text_refusal` và `file_writer`). Không chọn.
- **Chuyển phép kiểm lại vào `source.py`** (hàm công khai mới): thêm API vào `tools/` chỉ cho một nơi dùng, đụng làn 1 (`source.py`) đang có task khác; điều cần có đã nằm sẵn trong `resolve_safe_path`. Không chọn.
- **Bỏ kiểm lại trong `file_writer`**, chỉ dựa `check_block`: trái Ràng buộc `.git*`/symlink của ADR-040 và nới vành đai (khe giữa kiểm và ghi rộng hơn). Không chọn.

### Sai thì hoàn tác
Nếu `_refuse_unless_canonical` từ chối đường dẫn hợp lệ (ví dụ bench đặt dưới một đường dẫn có symlink mà `full_path` truyền vào không phải dạng `realpath`): sửa nơi dựng `full_path` cho dùng kết quả của `check_write_path` (vốn là `realpath`), không nới hàm. Bỏ hẳn phán quyết: đổi lại tên và thân hàm, gỡ luật `check_file_writer_rechecks_through_resolver` và hai ca tự kiểm; không có dữ liệu phải di trú.

---

## Phán quyết 2 (T23) = ADR-040 Phán quyết C-3

### Chọn
**Ngoại lệ có tên cho ADR-001, ở đúng một module, kèm luật hẹp cách dùng.** `erp_ai/agent/changes/restart_check.py` được import đúng hai thư viện ngoài `psutil` và `redis`; không khai vào `pyproject.toml` của `erp_ai` (phiên bản do frappe ghim: `apps/frappe/pyproject.toml:61` `psutil~=5.9.5`, `:69` `redis~=4.5.5`). Module chỉ được dùng: `psutil.Process` (đọc `create_time()`), `psutil.Error`, `redis.exceptions.RedisError`. Không gửi tín hiệu, không dựng client Redis.

Hợp đồng của T23 không đổi (`outcome`, `epoch_of_naive_utc`, `epoch_of_system_time`, `web_started`, `workers_started` như `tasks.md:218`). Mã ở `ad729a7` đã đúng hợp đồng và đúng tập tên cho phép (`restart_check.py:12-13`, `NO_EVIDENCE_ERRORS`, `web_started`).

### Vì
- ADR-001 cấm thư viện ngoài để mỗi phụ thuộc có chủ và đếm được; ngoại lệ có tên, một file, một tập thuộc tính giữ đúng mục đích đó.
- Thư viện chuẩn không thay được hai việc này một cách an toàn: thời điểm khởi động của tiến trình cha phải đọc `/proc/<ppid>/stat` (trường 22 theo tick) cộng `btime` của `/proc/stat` — mã riêng, chỉ Linux, không có lỗi kiểu rõ ràng; còn lỗi Redis của `get_workers()` chỉ bắt được bằng `except Exception`, che cả lỗi lập trình, làm "không có bằng chứng" thành bằng chứng sai. Lớp `redis.exceptions.ConnectionError` của redis-py không kế thừa `ConnectionError` của Python, nên không bắt hẹp được bằng thư viện chuẩn.
- Khai vào `pyproject.toml` của `erp_ai` là ghim thứ hai cạnh ghim của frappe: lệch khi nâng frappe thì bộ giải pip xung đột, và trái "không thêm phụ thuộc" của design §4.4 (STD-DEP-1).
- Vành đai không yếu đi: phương án R3 của ADR-040 (tự gửi tín hiệu) vẫn bị cấm, giờ bằng luật (không `kill`/`terminate`/`send_signal`…); module vẫn chỉ đọc.

### Luật kiến trúc
- **Đổi** `check_import_boundaries` (`test_architecture.py:537-550`) và chú thích ADR-001 ở dòng 157-158:
  - thêm hằng tay `NAMED_LIBRARY_IMPORTS = {"agent/changes/restart_check.py": frozenset({"psutil", "redis"})}` (ghi "ADR-040 Phán quyết C-3");
  - nhánh `elif target.split(".")[0] not in ALLOWED_TOP_LEVEL_MODULES` bỏ qua khi `target.split(".")[0] in NAMED_LIBRARY_IMPORTS.get(rel, ())`;
  - thêm vi phạm "ngoại lệ chết": file trong `NAMED_LIBRARY_IMPORTS` không còn tồn tại, hoặc không còn import một tên trong tập của nó.
  `ALLOWED_TOP_LEVEL_MODULES` và nhánh `anthropic` giữ nguyên.
- **Thêm** `check_restart_check_library_use(sources) -> list`: trong `agent/changes/restart_check.py`:
  - mọi tham chiếu thuộc tính có gốc `psutil` thuộc `{"psutil.Process", "psutil.Error"}`; có gốc `redis` thuộc `{"redis.exceptions", "redis.exceptions.RedisError"}`; `from psutil import …` / `from redis… import …` chỉ được các tên tương ứng;
  - không có lời gọi thuộc tính tên `kill`, `terminate`, `send_signal`, `suspend`, `resume`, `nice`, `ionice`, `rlimit`, `cpu_affinity`;
  - không có `subprocess`, `os.kill`, `os.killpg`, `signal.` (khớp "không subprocess" của §4.4).
- Ca tự kiểm:
  - `test_layer_imports` (dòng 4372): xanh trên mã thật, cộng `self.assertIn("import psutil", self.sources["agent/changes/restart_check.py"])`.
  - `test_import_boundaries_named_library_only_in_restart_check`: `import psutil` trong `agent/changes/apply_job.py` → bắt; `import redis` trong `agent/runner.py` → bắt; `import requests` trong `restart_check.py` → bắt; `import rq` trong `restart_check.py` → bắt; `import psutil\nimport redis\n` trong `restart_check.py` → `[]`; `from psutil import Process` trong `restart_check.py` → `[]`; `NAMED_LIBRARY_IMPORTS` trỏ tới file không import `redis` → bắt "ngoại lệ chết".
  - `test_restart_check_library_use` trên mã thật → `[]`; `test_restart_check_library_use_catches_signals_and_clients`: `psutil.Process(1).kill()` → bắt; `psutil.process_iter()` → bắt; `redis.Redis()` → bắt; `os.kill(1, 15)` → bắt.

### Dev phải sửa trên `ad729a7` (nhánh `team/CHG-002-task-23`)
1. `restart_check.py`, `test_restart_check.py`: không đổi (7 test đã xanh).
2. `erp_ai/tests/test_architecture.py`: đổi `check_import_boundaries`, thêm `check_restart_check_library_use` và các ca tự kiểm ở trên.
3. Chạy `test_one` cho `test_restart_check.py` **và** module `erp_ai.tests.test_architecture` (lock site chung) trước khi báo DONE. Sau đó review bình thường (T23 chưa review).

### Task đổi trong `tasks.md`
- **T23**: touchpoint thêm `erp_ai/tests/test_architecture.py`. Returns giữ nguyên, thêm câu "`psutil`/`redis` chỉ qua `psutil.Process`, `psutil.Error`, `redis.exceptions.RedisError` (ADR-040 C-3)". Expect thêm `ARCH::TestArchitecture::test_layer_imports`, `test_import_boundaries_named_library_only_in_restart_check`, `test_restart_check_library_use`, `test_restart_check_library_use_catches_signals_and_clients` xanh.
- T24, T25: không đổi chữ; hết bị chặn khi T23 tick.

### Phương án khác
- **Chỉ thư viện chuẩn và frappe** (`/proc` cho web, `except Exception` cho worker): lý do ở mục "Vì". Không chọn.
- **Khai `psutil`, `redis` vào `pyproject.toml`**: ghim thứ hai, STD-DEP-1; vẫn phải sửa luật vì luật hiện chỉ cho `anthropic`. Không chọn.
- **Mở `psutil`, `redis` cho cả `erp_ai/**`**: mở đường cho tự gửi tín hiệu (R3 đã bị bác) ở bất kỳ module nào. Không chọn.
- **Bỏ bằng chứng web, chỉ dùng worker**: trái ADR-040 Quyết định 7 ("tiến trình của cả hai nhóm khởi động sau thời điểm gửi lệnh"). Không chọn.

### Sai thì hoàn tác
Nếu một bản nâng frappe bỏ `psutil` hoặc `redis`, `import` của `restart_check` lỗi và `test_restart_check.py` đỏ ngay ở CI (không lỗi ngầm): khi đó viết ADR mới (khai phụ thuộc, hoặc đường thư viện chuẩn). Bỏ hẳn phán quyết: gỡ `NAMED_LIBRARY_IMPORTS`, `check_restart_check_library_use` và các ca tự kiểm, thay hai hàm đọc bằng phương án thư viện chuẩn; không có dữ liệu phải di trú (trường kết quả restart giữ nguyên giá trị).

---

## Tự phản biện
- Hai task cùng tuân mọi ADR mà vẫn xung đột: T5 và T23 cùng sửa `erp_ai/tests/test_architecture.py` song song. Hai luật ở hai hàm khác nhau, không chung hằng; xung đột chỉ là văn bản khi merge. Tech-lead merge lần lượt và chạy lại module kiến trúc sau mỗi merge.
- T6 thêm tên vào `FILE_WRITER_RECHECKERS` sau T5 (T6 phụ thuộc T5), không chạy song song.
- Một hàm mới trong `file_writer` (ví dụ đổi tên file ở task sau) mà quên kiểm lại: luật chỉ phủ tên có trong `FILE_WRITER_RECHECKERS`. Ràng buộc C-2 đòi mọi hàm cấp module của `file_writer.py` có lời gọi `os.mkdir`, `os.rmdir`, `os.remove`, `os.unlink`, `os.replace`, `os.rename` hoặc `tempfile.mkstemp` phải có tên trong `FILE_WRITER_RECHECKERS` (trừ đường trả lại bên trong `make_parents`). Luật thêm điều kiện này như vi phạm thứ 4; ca tự kiểm: một hàm `rename_file` gọi `os.replace` không có tên trong hằng → bắt. Ở T5, `write_atomic` và `remove_created` chưa đổi nên điều kiện thứ 4 **bật từ T6**; T5 ghi `FILE_WRITER_RECHECKS_ALL = False`, T6 đặt `True` (hằng tay, xóa ở T49).

AC không đổi. Vành đai: chặt hơn ở C-2 (`TEN_CAM`, symlink ở thành phần cuối, kiểm trước `mkdir`), bằng ở C-3 (thêm luật cấm gửi tín hiệu).
