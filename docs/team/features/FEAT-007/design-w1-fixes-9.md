# FEAT-007 — design-w1-fixes-9: phán ba điểm của pre-flight đợt 1 (F-3, F-11, F-12)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu.
- Đầu vào: `preflight-w1.md:25` (F-3), `:32` (F-11), `:33` (F-12); `tasks.md:745-749` (T80), `:761-765` (T83); `design-addendum-1-U1.md:196-205`, `:255-263`, `:425-445`.
- Mã đọc (chỉ đọc, `git show`/`git grep`): `team/FEAT-007` @ `caa555a` — `erp_ai/agent/changes/test_result_comment.py:10-27` (import), `:43-44`, `:313-350` (`TestResultIsNotAnInstruction`); `erp_ai/agent/changes/result_comment.py:20`, `:100` (`COMMENT_TYPE_INFO`); `erp_ai/agent/authority.py:18-25` (`ticket_comment_filters`), `:44-100` (`is_instruction`, `run_instructor`, `_trigger_comment_author`, `latest_instructor`); `erp_ai/agent/test_authority.py:8-15`, `:144-203`; `git grep latest_instructor` (mọi file `.py`); `erp_ai/agent/policy.py:75-160`; `erp_ai/tests/test_architecture.py:154-157` (`CONFIG_CONTROLLER_FILES`), `:169-177` (`POLICY_FIELDS`), `:410-437`, `:501-524`, `:805-822`, `:4450`, `:4518-4522`, `:5583-5587`, `:6102-6118`; `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:60`, `:63`, `:228-229`, `:309-329`; `erp_ai/erp_ai_agent/report/erp_ai_cost/erp_ai_cost.py:116-136`; `erp_ai/tasks.py:69-76`.
- Không đổi kiến trúc: theo ADR-030 QĐ 4 (một vị từ dưới ngưỡng, ở `policy`), QĐ 6 (người ra lệnh chỉ từ sự kiện xếp hàng lần chạy), ADR-030 Ràng buộc (không còn hàm quét N comment chọn người ra lệnh; ngưỡng và ngân sách chỉ so ở `policy.py`; luật trường cho phép controller), ADR-003/ADR-005 (luật trường chính sách). Không đổi quy tắc nghiệp vụ. Không có `DESIGN_CONFLICT`.

---

## Điểm 1 — F-3, T80: `test_result_comment.py` còn gọi `authority.latest_instructor`

### Hiện trạng (dữ kiện)
- `test_result_comment.py:329-350` (`test_result_activity_enqueues_no_agent_run_and_is_not_an_instruction`): dòng kết quả do `result_comment.post_result` ghi là `Comment` loại `Info` (`result_comment.py:20`, `:100`), người ghi là `INSTRUCTOR` (`frappe.set_user(INSTRUCTOR)` ở `:332`). `:341` khẳng định dòng đó không làm ai thành người ra lệnh; `:350` khẳng định cùng chữ ấy dưới dạng `Comment` người thật của cùng người **thì** là chỉ thị. Chú thích `:343-344`: hai số 0 phía trên đến từ loại `Info`, không phải từ cách dựng test.
- `INSTRUCTOR` có vai trò người ra lệnh (`:43-44`), nên `authority.is_instruction(INSTRUCTOR, ticket)` là `True` với **cả hai** comment: `is_instruction` không phân biệt được `Info` với `Comment` → không dùng được làm khẳng định thay thế (ca `:341` sẽ thành `True` hoặc phải bỏ).
- `authority.run_instructor` đã có trên nhánh (`authority.py:73-83`). Với `TRIGGER_COMMENT_MENTION` nó đọc `owner` của đúng comment `comment_name` qua `ticket_comment_filters` (`:18-25`, có `comment_type == "Comment"`) → comment `Info` trả `None`, comment người thật của `INSTRUCTOR` trả `INSTRUCTOR`. Đây đúng là đường của ADR-030 QĐ 6 mà T80 dùng ở runner, và giữ nguyên ý của test: `None` chỉ do loại `Info`.
- `git grep latest_instructor` còn chỉ ra ngoài preflight: `test_authority.py:163` (`test_spoofed_comment_author_fields_ignored`), `:203` (`test_comments_read_from_core_comment_only`) — hai test này không phải test bị xóa (`:144`); và 24 chỗ `patch.object(authority, "latest_instructor", …)` trong `test_agent_runner.py` (`:852` … `:3002`). Cả hai file đã nằm trong `files:` của T80; sau khi xóa hàm, `patch.object` lên thuộc tính không tồn tại ném `AttributeError`. Phán luôn ở đây để T80 không còn lựa chọn mở.

### Phán quyết
1. `test_result_comment.py` — thay đúng hai khẳng định, không đổi khẳng định nào khác:
   - `:341` `self.assertIsNone(authority.latest_instructor(self.ticket))` → `self.assertIsNone(authority.run_instructor(self.ticket, TRIGGER_COMMENT_MENTION, comment))`
   - `:350` `self.assertEqual(authority.latest_instructor(self.ticket), INSTRUCTOR)` → `self.assertEqual(authority.run_instructor(self.ticket, TRIGGER_COMMENT_MENTION, human), INSTRUCTOR)`
   - Import: thêm `TRIGGER_COMMENT_MENTION,` vào khối `from erp_ai.constants import (` ngay sau `ROLE_INSTRUCTOR,` (`:25`; thứ tự chữ cái của khối).
2. `test_authority.py` (đã thuộc T80; `TRIGGER_COMMENT_MENTION` đã import ở `:12`):
   - `:163` → `self.assertIsNone(authority.run_instructor(self.ticket_p, TRIGGER_COMMENT_MENTION, name))` (comment của `PLAIN` giả `comment_email`/`comment_by` của `INSTRUCTOR` → vẫn không là người ra lệnh).
   - `:203` → `self.assertIsNone(authority.run_instructor(self.ticket_p, TRIGGER_COMMENT_MENTION, legacy.name))` (tên của bảng cũ `HD Ticket Comment` có `commented_by=INSTRUCTOR` không bao giờ thành người ra lệnh).
3. `test_agent_runner.py` (đã thuộc T80): mọi `patch.object(authority, "latest_instructor", return_value=X)` đổi đích vá thành `"run_instructor"`, giữ nguyên `return_value` và mọi khẳng định (mock không đọc tham số; chữ ký mới ba tham số không ảnh hưởng).
4. T80 thêm `erp_ai/agent/changes/test_result_comment.py` vào `files:`. Lý do trong commit: ADR-030 QĐ 6, NFR-8 (hàm bị xóa, khẳng định giữ nghĩa).
5. Thứ tự đỏ/xanh: các khẳng định mới xanh ngay cả trước khi xóa hàm (`run_instructor` đã có). Bằng chứng đỏ của F-3 là: xóa `latest_instructor` trước khi sửa test → `cmd.test_one` của `test_result_comment.py` ra `AttributeError: module 'erp_ai.agent.authority' has no attribute 'latest_instructor'`; sửa theo mục 1 → xanh cả file.

### Dòng task thay thế (chép nguyên văn) — T80

Chỉ phần F-3; phán quyết của F-4, F-5, F-6 (người phán khác) chèn thêm vào cùng dòng khi có.

```
- [ ] T80 — Runner dựng context từ `policy` và `run_instructor` — files: erp_ai/agent/runner.py, erp_ai/agent/authority.py, erp_ai/agent/test_authority.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/changes/test_result_comment.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/test_agent_runner.py — depends: T75, T77, T72, T69
  - Tiêu chí: AC-13 (đầu-cuối); `U1.md:259-260`, `:207`; F-3 theo `design-w1-fixes-9.md` Điểm 1.
  - Receives: T66–T69, T73, T75, T76.
  - Returns: `_run` bước (e) và context theo `U1.md:259-260` (lần chạy không tạo phiếu đọc `latest_classification`); xóa `authority.latest_instructor` và test `test_latest_instructor_prefers_latest_comment_then_owner` (lý do trong commit: ADR-030 QĐ 6, NFR-8). Mọi chỗ khác gọi hàm đã xóa đổi sang `run_instructor`, không đổi khẳng định nào khác: `test_result_comment.py:341` → `self.assertIsNone(authority.run_instructor(self.ticket, TRIGGER_COMMENT_MENTION, comment))`, `:350` → `self.assertEqual(authority.run_instructor(self.ticket, TRIGGER_COMMENT_MENTION, human), INSTRUCTOR)`, thêm `TRIGGER_COMMENT_MENTION,` sau `ROLE_INSTRUCTOR,` trong khối import `erp_ai.constants` (`:25`); `test_authority.py:163` → `self.assertIsNone(authority.run_instructor(self.ticket_p, TRIGGER_COMMENT_MENTION, name))`, `:203` → `self.assertIsNone(authority.run_instructor(self.ticket_p, TRIGGER_COMMENT_MENTION, legacy.name))`; `test_agent_runner.py`: mọi `patch.object(authority, "latest_instructor", return_value=X)` → `patch.object(authority, "run_instructor", return_value=X)`, giữ `return_value` (dòng số đo ở `team/FEAT-007` @ `caa555a`).
  - Expect: `TestRunnerGrant::test_plain_user_mention_after_instructor_gets_no_write_tools`; `erp_ai/tests/test_architecture.py::test_authority_has_no_comment_scan_for_instructor` xanh. Đỏ F-3: xóa `latest_instructor` trước khi sửa `test_result_comment.py` → `cmd.test_one` của file đó ra `AttributeError: module 'erp_ai.agent.authority' has no attribute 'latest_instructor'`; sửa hai khẳng định → xanh. `cmd.test_one` xanh cả file: `erp_ai/agent/changes/test_result_comment.py`, `erp_ai/agent/test_authority.py`, `erp_ai/agent/test_agent_runner.py`. Ngoài `erp_ai/tests/test_architecture.py`, `git grep -n latest_instructor -- '*.py'` trên nhánh task ra 0 dòng.
```

---

## Phần chung của Điểm 2 và Điểm 3 — "phép so sánh" là gì

Hai luật mới cùng một định nghĩa, viết ở `erp_ai/tests/test_architecture.py` cạnh `check_policy_fields_only_in_policy` (`:805`), dùng lại `only_python`, `parse`, `referenced_name`, `violation` (`:430`, `:501-524`; STD-DESIGN-4):

```python
ORDERING_OPS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)


def operand_names(node) -> set:
	"""referenced_name of every Name/Attribute inside one compare operand, plus every str Constant inside it."""
	names = set()
	for child in ast.walk(node):
		name = referenced_name(child)
		if name:
			names.add(name)
		elif isinstance(child, ast.Constant) and isinstance(child.value, str):
			names.add(child.value)
	return names


def ordering_compares(tree: ast.AST):
	"""Every Compare node with at least one <, <=, >, >= (is/in/==/!= alone are not a threshold or budget decision)."""
	for node in ast.walk(tree):
		if isinstance(node, ast.Compare) and any(isinstance(op, ORDERING_OPS) for op in node.ops):
			yield node
```

- **Phép so sánh** = một nút `ast.Compare` có ít nhất một toán tử `<`, `<=`, `>`, `>=`. Toán hạng = `left` và từng phần tử của `comparators`; một toán hạng "nêu" một tên khi tên đó có trong `operand_names(toán hạng)` (tên biến, tên thuộc tính, hoặc hằng chuỗi đúng bằng tên, ở bất kỳ độ sâu nào của toán hạng — vậy `frappe.db.get_single_value(..., "spent_this_month_usd") > x` và `policy.confidence_threshold(s) > p` đều tính).
- **Không phải** phép so sánh: gán, gọi hàm, đối số từ khóa, khóa dict, `return` một giá trị, `is`/`is not`/`in`/`not in`/`==`/`!=`, kiểm thật/giả (`if x:`). Vì thế đọc để hiển thị, ghi, khôi phục, khai báo bảng khoảng giá trị và chuyển giá trị vào hàm của `policy` không bao giờ bị bắt.
- Phạm vi quét: `self.sources` (`load_product_sources`, `:420`: bỏ mọi file test và thư mục `tests/`), trừ đúng một file `POLICY_FILE` (`agent/policy.py`). Không miễn file nào khác.
- Giới hạn đã biết (chấp nhận, không mở): luật là AST thuần, không lần theo dữ liệu — `spent = …; if spent > budget:` với biến cục bộ tên khác không bị bắt; `min()`/`max()`/`sorted()` không tính là so sánh. Người duyệt (reviewer) vẫn soát theo ADR-030 Ràng buộc.

---

## Điểm 2 — F-11, T83: luật `test_threshold_compared_only_in_policy`

### Hiện trạng (dữ kiện)
- `U1.md:431` tả luật là "grep `confidence_threshold` / `confidence_pct <` ngoài `policy.py` → finding". Đọc theo chữ (grep tên) thì bắt `erp_ai_setting.py:63` (khóa dict `"confidence_threshold": ("Ngưỡng độ tin cậy", 0, 100)` của `INT_LIMITS`) và dòng runner `threshold = policy.confidence_threshold(settings)` mà `U1.md:259` đòi.
- Việc **đọc** trường `confidence_threshold` đã có luật khác lo: T83 thêm `confidence_threshold` vào `POLICY_FIELDS`; `check_policy_fields_only_in_policy` đã miễn lời gọi hàm của `policy` (`:815-816`, `resolved_name == "erp_ai.agent.policy.confidence_threshold"`), và T83 cho phép controller (`U1.md:443`, ADR-030 Ràng buộc). Phần đó của dòng T83 không đổi. Luật mới chỉ lo **so sánh** (ADR-030 QĐ 4: vị từ dưới ngưỡng duy nhất là `policy.is_below_confidence`).
- Controller so khoảng bằng biến chung `value`, `low`, `high` (`erp_ai_setting.py:309-311`), không nêu tên ngưỡng. `policy.py` có `CONFIDENCE_THRESHOLD_FIELD`, `DEFAULT_CONFIDENCE_THRESHOLD`, `_known_pct`, `pct < threshold` (`:116-146`) — miễn vì là `POLICY_FILE`.
- `git grep` trên `caa555a` (mã sản phẩm, ngoài `policy.py`): `confidence_threshold` chỉ ở `erp_ai_setting.py:63` (khóa dict); `confidence_pct` chỉ ở `install.py:158` (khóa dict `"fieldname": "ai_confidence_pct"`) và `patches/feat007_unknown_confidence_pct.py:1`, `:19-20` (docstring, chuỗi SQL làm đối số); từ `threshold` 0 dòng; `do_tin_cay_pct`, `below_threshold` 0 dòng. Không chỗ nào nằm trong một `Compare` → luật xanh trên mã đã merge. Mã U1 sắp merge (T72, T80, T81) cũng không bị bắt nếu theo thiết kế: `threshold = policy.confidence_threshold(settings)` (gán), `below_threshold=policy.is_below_confidence(pct, threshold, …)` (đối số), `if not context.below_threshold` (không phải `Compare`; `below_threshold` không khớp tên), `predicted_confidence_pct=classification.confidence_pct` (đối số), kiểm khoảng của `parse_classification` theo `CONFIDENCE_PCT_MIN`/`CONFIDENCE_PCT_MAX` (`U1.md:252-253`, miễn ở dưới).

### Phán quyết — luật bắt gì, miễn gì

```python
CONFIDENCE_EXACT_NAMES = ("threshold", "do_tin_cay_pct")
CONFIDENCE_RANGE_BOUNDS = ("CONFIDENCE_PCT_MIN", "CONFIDENCE_PCT_MAX")


def is_confidence_name(name: str) -> bool:
	lowered = name.lower()
	return (
		lowered in CONFIDENCE_EXACT_NAMES
		or "confidence_threshold" in lowered
		or lowered.endswith("confidence_pct")
	)


def check_threshold_compared_only_in_policy(sources: dict) -> list:
	"""ADR-030 QĐ 4: a confidence value is compared with a threshold only in agent/policy.py."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel == POLICY_FILE:
			continue
		for compare in ordering_compares(parse(rel, source)):
			operands = [compare.left, *compare.comparators]
			matched = [o for o in operands if any(is_confidence_name(n) for n in operand_names(o))]
			if not matched:
				continue
			others = [o for o in operands if all(o is not m for m in matched)]
			if len(matched) == 1 and others and all(referenced_name(o) in CONFIDENCE_RANGE_BOUNDS for o in others):
				continue  # range check of a parsed pct against its declared bounds (classification.py)
			name = sorted(n for n in operand_names(matched[0]) if is_confidence_name(n))[0]
			violations.append(violation(rel, compare, f"compares {name} outside {POLICY_FILE}"))
	return violations
```

- **Bắt**: mọi phép so sánh (định nghĩa chung) ngoài `agent/policy.py` có một toán hạng nêu tên khớp `is_confidence_name`: đúng `threshold` (không phân biệt hoa thường), đúng `do_tin_cay_pct` (khóa JSON của phân loại), mọi tên chứa `confidence_threshold` (`confidence_threshold`, `CONFIDENCE_THRESHOLD_FIELD`, `DEFAULT_CONFIDENCE_THRESHOLD`), mọi tên tận cùng bằng `confidence_pct` (`confidence_pct`, `predicted_confidence_pct`, `ai_confidence_pct`). So với số viết cứng (`c.confidence_pct < 70`) cũng bị bắt.
- **Miễn** (chỉ hai thứ):
  1. File `agent/policy.py`.
  2. Kiểm khoảng của một giá trị độ tin cậy với hai mốc đã khai: phép so sánh có **đúng một** toán hạng khớp, có ít nhất một toán hạng khác, và mọi toán hạng khác là tên `CONFIDENCE_PCT_MIN` hoặc `CONFIDENCE_PCT_MAX` (ví dụ `CONFIDENCE_PCT_MIN <= confidence_pct <= CONFIDENCE_PCT_MAX`). Viết khoảng bằng số `0 <= confidence_pct <= 100` ngoài `policy.py` thì bị bắt (U1.md:253 đã đặt hai hằng; T83 khi đó trả `DESIGN_CONFLICT` theo dòng Returns).
- **Không cần miễn** (không phải phép so sánh): lời gọi `policy.confidence_threshold(...)`, `policy.is_below_confidence(...)`; bảng `INT_LIMITS` của controller (`erp_ai_setting.py:63`) và vòng kiểm `value < low` (`:309-311`). Không miễn theo file cho controller ở luật này.
- Thông điệp: `"<file>:<dòng>: compares <tên> outside agent/policy.py"` (`<tên>` là tên khớp nhỏ nhất theo thứ tự chữ của toán hạng khớp đầu tiên).

### Test
- `erp_ai/tests/test_architecture.py::TestArchitecture::test_threshold_compared_only_in_policy` (lớp `:4450`, theo mẫu `:4518-4522`): `self.assertIn("confidence_threshold", self.sources[POLICY_FILE])`; `self.assertEqual(check_threshold_compared_only_in_policy(self.sources), [])`.
- `erp_ai/tests/test_architecture.py::TestScannersCatchViolations::test_threshold_scanner_catches_comparison_outside_policy_and_allows_reads` (lớp `:5583`, `assertCaught`, theo mẫu `:6102-6118`). Mỗi ca trong `subTest(source=…)`:
  - Bắt (`self.assertCaught(check_threshold_compared_only_in_policy({rel: source}), fragment)`):
    - `"agent/runner.py"`, `"def f(settings, pct):\n\treturn pct < settings.confidence_threshold\n"`, mảnh `"agent/runner.py:2: compares confidence_threshold outside agent/policy.py"`
    - `"agent/tools/registry.py"`, `"def f(classification, threshold):\n\treturn classification.confidence_pct < threshold\n"`, mảnh `"compares confidence_pct"`
    - `"agent/tools/route_ticket.py"`, `"def f(c):\n\treturn c.confidence_pct < 70\n"`, mảnh `"compares confidence_pct"`
    - `"agent/runner.py"`, `"from erp_ai.agent import policy\ndef f(s, p):\n\treturn policy.confidence_threshold(s) > p\n"`, mảnh `"compares confidence_threshold"`
    - `"agent/classification.py"`, `"def f(data):\n\treturn 0 <= data['do_tin_cay_pct'] <= 100\n"`, mảnh `"compares do_tin_cay_pct"`
  - Cho phép (`self.assertEqual(check_threshold_compared_only_in_policy({rel: source}), [])`):
    - `"agent/runner.py"`, `"from erp_ai.agent import policy\ndef f(settings, pct):\n\tthreshold = policy.confidence_threshold(settings)\n\treturn policy.is_below_confidence(pct, threshold, has_instructor=True, act_now=False)\n"`
    - `"erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py"`, `"INT_LIMITS = {'confidence_threshold': ('Ngưỡng độ tin cậy', 0, 100)}\ndef f(doc):\n\tfor fieldname, (label, low, high) in INT_LIMITS.items():\n\t\tvalue = doc.get(fieldname)\n\t\tif value < low or (high is not None and value > high):\n\t\t\treturn label\n"`
    - `"agent/classification.py"`, `"CONFIDENCE_PCT_MIN = 0\nCONFIDENCE_PCT_MAX = 100\ndef f(confidence_pct):\n\treturn CONFIDENCE_PCT_MIN <= confidence_pct <= CONFIDENCE_PCT_MAX\n"`
    - `"agent/runner.py"`, `"def f(c):\n\treturn c.confidence_pct is None\n"`
    - `POLICY_FILE`, `"def f(pct, threshold):\n\treturn pct is None or pct < threshold\n"`
- Đỏ trước: thêm test của `TestScannersCatchViolations` trước khi có hàm → `NameError: name 'check_threshold_compared_only_in_policy' is not defined`.

---

## Điểm 3 — F-12, T83: luật `test_no_spent_comparison_outside_policy`

### Hiện trạng (dữ kiện)
- `U1.md:440` để trống ô mô tả. AC-61: vượt ngân sách đọc từ ERP AI Log (`policy.month_spend_usd`), không đọc `spent_this_month_usd`; vị từ duy nhất là `policy.is_over_budget` (`policy.py:86-88`: `month_spend_usd(now) > (settings.monthly_budget_usd or 0)`).
- Mã đã merge nêu `spent_this_month_usd` ngoài `policy.py` ở ba chỗ, không chỗ nào là phép so sánh: `erp_ai_agent/report/erp_ai_cost/erp_ai_cost.py:130` (gán `spent = frappe.db.get_single_value(…, "spent_this_month_usd", cache=False)`, `:136` đưa vào dòng hiển thị), `tasks.py:76` (đối số của `frappe.db.set_single_value`), `erp_ai_setting.py:228-229` (gán khôi phục). `monthly_budget_usd` ngoài `policy.py` chỉ ở `erp_ai_setting.py:60` (khóa dict `INT_LIMITS`; kiểm khoảng bằng `value` ở `:309-311`). `month_spend_usd` ngoài `policy.py` 0 dòng; `runner.py:164` gọi `policy.is_over_budget(settings)`.

### Phán quyết — luật bắt gì, miễn gì

```python
SPEND_NAMES = ("spent_this_month_usd", "monthly_budget_usd", "month_spend_usd")


def check_no_spent_comparison_outside_policy(sources: dict) -> list:
	"""AC-61, ADR-030: spend is compared with the budget only in agent/policy.py (policy.is_over_budget)."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel == POLICY_FILE:
			continue
		for compare in ordering_compares(parse(rel, source)):
			for operand in [compare.left, *compare.comparators]:
				names = sorted(operand_names(operand) & set(SPEND_NAMES))
				if names:
					violations.append(violation(rel, compare, f"compares {names[0]} outside {POLICY_FILE}"))
					break
	return violations
```

- **"So sánh tổng chi"** = phép so sánh (định nghĩa chung) ngoài `agent/policy.py` có một toán hạng nêu đúng một trong ba tên `spent_this_month_usd`, `monthly_budget_usd`, `month_spend_usd` (tên, thuộc tính, hoặc hằng chuỗi đúng bằng tên, ở mọi độ sâu của toán hạng; khớp chính xác, có phân biệt hoa thường). Mỗi `Compare` báo tối đa một lần.
- **Miễn file**: chỉ `agent/policy.py`. Không miễn báo cáo, `tasks.py` hay controller: đọc để hiển thị (`erp_ai_cost.py:130`), ghi (`tasks.py:76`), khôi phục (`erp_ai_setting.py:228`), khai bảng `INT_LIMITS` (`erp_ai_setting.py:60`) không phải phép so sánh nên không bị bắt; một phép so sánh chi/ngân sách mới trong các file đó thì bị bắt, đúng ý AC-61. Kiểm khoảng của controller đi qua `INT_LIMITS` và biến `value` (`:309-311`); thêm kiểm khoảng theo tên trường (`self.monthly_budget_usd < 0`) là đi ngược mẫu đó và bị bắt.
- Thông điệp: `"<file>:<dòng>: compares <tên> outside agent/policy.py"`.
- Không gộp với luật ngưỡng (hai tập tên, hai AC: AC-22 và AC-61); dùng chung `ORDERING_OPS`, `operand_names`, `ordering_compares`.

### Test
- `erp_ai/tests/test_architecture.py::TestArchitecture::test_no_spent_comparison_outside_policy`: `self.assertIn("monthly_budget_usd", self.sources[POLICY_FILE])`; `self.assertEqual(check_no_spent_comparison_outside_policy(self.sources), [])`.
- `erp_ai/tests/test_architecture.py::TestScannersCatchViolations::test_spent_scanner_catches_comparison_outside_policy_and_allows_reads`. Mỗi ca trong `subTest(source=…)`:
  - Bắt (`self.assertCaught(check_no_spent_comparison_outside_policy({rel: source}), fragment)`):
    - `"agent/runner.py"`, `"def f(settings):\n\treturn settings.spent_this_month_usd > settings.monthly_budget_usd\n"`, mảnh `"agent/runner.py:2: compares spent_this_month_usd outside agent/policy.py"`
    - `"erp_ai_agent/report/erp_ai_cost/erp_ai_cost.py"`, `"import frappe\ndef f(budget):\n\treturn frappe.db.get_single_value('ERP AI Setting', 'spent_this_month_usd', cache=False) >= budget\n"`, mảnh `"compares spent_this_month_usd"`
    - `"agent/tools/registry.py"`, `"from erp_ai.agent import policy\ndef f(settings, spend):\n\treturn spend > settings.monthly_budget_usd\n"`, mảnh `"compares monthly_budget_usd"`
    - `"agent/runner.py"`, `"from erp_ai.agent import policy\ndef f(limit):\n\treturn policy.month_spend_usd() > limit\n"`, mảnh `"compares month_spend_usd"`
  - Cho phép (`self.assertEqual(check_no_spent_comparison_outside_policy({rel: source}), [])`):
    - `"erp_ai_agent/report/erp_ai_cost/erp_ai_cost.py"`, `"import frappe\ndef f():\n\tspent = frappe.db.get_single_value('ERP AI Setting', 'spent_this_month_usd', cache=False)\n\treturn [('Đã chi', spent)]\n"`
    - `"tasks.py"`, `"import frappe\ndef f(spent_by_label):\n\tfrappe.db.set_single_value('ERP AI Setting', 'spent_this_month_usd', sum(spent_by_label.values()))\n"`
    - `"erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py"`, `"import frappe\nINT_LIMITS = {'monthly_budget_usd': ('Ngân sách tháng', 0, None)}\ndef f(doc):\n\tdoc.spent_this_month_usd = frappe.db.get_single_value('ERP AI Setting', 'spent_this_month_usd', cache=False)\n"`
    - `"agent/runner.py"`, `"from erp_ai.agent import policy\ndef f(settings):\n\treturn policy.is_over_budget(settings)\n"`
    - `"agent/runner.py"`, `"def f(settings):\n\treturn settings.spent_this_month_usd is None\n"`
    - `POLICY_FILE`, `"def f(settings, spend):\n\treturn spend > (settings.monthly_budget_usd or 0)\n"`
- Đỏ trước: thêm test của `TestScannersCatchViolations` trước khi có hàm → `NameError: name 'check_no_spent_comparison_outside_policy' is not defined`.

---

## Dòng task thay thế (chép nguyên văn) — T83

```
- [ ] T83 — Luật kiến trúc của U1 — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T82
  - Tiêu chí: ADR-030 Ràng buộc, QĐ 4; AC-22, AC-61; `U1.md:401`, `:431`, `:440`, `:443`; C-2 (không có `site_environment` trong `POLICY_FIELDS`); F-11, F-12 theo `design-w1-fixes-9.md` Điểm 2, Điểm 3 (định nghĩa "phép so sánh": phần chung).
  - Receives: mã U1 đã merge (T66–T82).
  - Returns: `POLICY_FIELDS` thêm `record_tools_enabled`, `act_now_enabled`, `one_click_approval_enabled`, `level_cap_a`..`level_cap_f`, `confidence_threshold`; luật cho phép `erp_ai_setting.py`; ba luật mới. Hai luật so sánh dùng chung `ORDERING_OPS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)`, `operand_names(node)`, `ordering_compares(tree)`; quét `only_python(sources)` trừ đúng `POLICY_FILE`, không miễn file nào khác; chỉ nút `ast.Compare` có toán tử thứ tự mới tính (gán, gọi hàm, đối số, khóa dict, `is`/`in`/`==`/`!=` không tính). `check_threshold_compared_only_in_policy(sources) -> list`: bắt toán hạng nêu tên khớp `is_confidence_name` (đúng `threshold` hoặc `do_tin_cay_pct`, chứa `confidence_threshold`, tận cùng `confidence_pct`, không phân biệt hoa thường); miễn đúng ca một toán hạng khớp và mọi toán hạng khác là `CONFIDENCE_PCT_MIN`/`CONFIDENCE_PCT_MAX`. `check_no_spent_comparison_outside_policy(sources) -> list`: bắt toán hạng nêu đúng `spent_this_month_usd`, `monthly_budget_usd` hoặc `month_spend_usd`. Thông điệp cả hai: `"<file>:<dòng>: compares <tên> outside agent/policy.py"`. Thân hàm theo `design-w1-fixes-9.md` Điểm 2, Điểm 3. Luật mới bắt được vi phạm trong mã đã merge → trả `DESIGN_CONFLICT` kèm danh sách, không sửa mã nguồn.
  - Expect: `TestArchitecture::test_runner_takes_tools_and_flags_from_grant`, `::test_threshold_compared_only_in_policy`, `::test_no_spent_comparison_outside_policy` xanh. Mỗi luật so sánh có ca đỏ bằng chuỗi mẫu: đỏ trước — thêm `TestScannersCatchViolations::test_threshold_scanner_catches_comparison_outside_policy_and_allows_reads` và `::test_spent_scanner_catches_comparison_outside_policy_and_allows_reads` trước khi có hàm → `NameError: name 'check_threshold_compared_only_in_policy' is not defined` / `NameError: name 'check_no_spent_comparison_outside_policy' is not defined`; viết hàm → xanh. Chuỗi mẫu phải bắt: `"def f(settings, pct):\n\treturn pct < settings.confidence_threshold\n"` ở `agent/runner.py` → `agent/runner.py:2: compares confidence_threshold outside agent/policy.py`; `"def f(settings):\n\treturn settings.spent_this_month_usd > settings.monthly_budget_usd\n"` ở `agent/runner.py` → `agent/runner.py:2: compares spent_this_month_usd outside agent/policy.py`; đủ các ca bắt và cho phép liệt kê ở `design-w1-fixes-9.md` Điểm 2 mục Test, Điểm 3 mục Test (trong đó dòng runner `threshold = policy.confidence_threshold(settings)`, bảng `INT_LIMITS` của controller, `erp_ai_cost.py:130`, `tasks.py:76`, `erp_ai_setting.py:228` là ca cho phép). `cmd.test_one` của `erp_ai/tests/test_architecture.py` xanh cả file.
```
