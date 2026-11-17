# Tag-Based Assignee Table (CHG-011) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ERP AI Setting gets a table "Gán người theo tag" (tag → HD Agent, optional category); when the bot routes a ticket it gives the ticket (and its C/D Task) to the person of the first tag that has a row, before the old `routing_rules`.

**Architecture:** A new child DocType `ERP AI Tag Assignee` on ERP AI Setting (field `tag_assignees`). `routing.decide_route` stays pure code (no model): it takes the ticket's tags and the table rows, picks the person, and records which tag decided in a new `RouteDecision.assignee_tag`. The runner passes the ticket's own tags plus the model's labels, always shows the table's tags in the classify request's label catalog, and names the tag in the route comment and the assign action.

**Tech Stack:** Frappe 15 (Python 3, tabs), Helpdesk, Frappe test runner on the shared dev site `miyano`.

**Spec:** `docs/superpowers/specs/2026-11-17-tag-assignee-design.md` (approved by the user 2026-11-17).

## Global Constraints

- Worktree `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/chg-011`, branch `team/CHG-011` from `develop`. Absolute paths and `git -C`; never `cd` into the worktree; never touch the main checkout (other sessions work there; `team/BUG-007` is open in parallel and edits `erp_ai/agent/tools/write_ticket.py` — this plan does not touch that file).
- The spec and this plan are untracked files in the main checkout: **move** them (not copy) into the same paths in the worktree and commit them as the branch's first commit, so the later merge does not collide with untracked files.
- Scratchpad `SP=/tmp/claude-1000/-home-miyano-frappe-bench-apps-erp-ai/17ddc734-89b7-4a5d-a9ec-a88ee37d7f7c/scratchpad`. Create two scripts there (chmod +x):
  - `$SP/wt-test.sh <WT> <dotted.module>...`: from `/home/miyano/frappe-bench`, per module `PYTHONPATH=$WT flock apps/erp_ai/.team/miyano-site.lock bench --site miyano run-tests --module "$m"`; exit non-zero if any failed.
  - `$SP/wt-sync.sh <WT>`: from `/home/miyano/frappe-bench`, for `dn` in `erp_ai_tag_assignee erp_ai_setting` (that order): `PYTHONPATH=$WT flock apps/erp_ai/.team/miyano-site.lock bench --site miyano execute frappe.reload_doc --kwargs "{'module': 'ERP AI agent', 'dt': 'doctype', 'dn': '$dn', 'force': True}"`.
- Tests only through `wt-test.sh`; Bash timeout ≥ 1500000 ms. Never `bench migrate`, never `bench build`, never the whole app. The only site schema change is `wt-sync.sh` (additive: one new table, one new field). If a test errors on a missing `tabERP AI Tag Assignee` or `tag_assignees`, another session's migrate overwrote the meta: run `wt-sync.sh` again.
- TDD per `CLAUDE.md`: failing test first, seen failing for the right reason. No skip/xfail. An existing assertion changes only where a task says so, with a `# CHG-011: ...` comment.
- Python indented with tabs, style of the surrounding file. Vietnamese strings exactly as written here.
- Commits small, conventional, `(CHG-011)` suffix, each ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Run `pre-commit run --files <changed files>` before each commit. Never push or merge.
- Person choice stays code-only: no model call, no prompt text decides the person. The 400-character cap on field descriptions holds.

## Review Focus

1. A row whose person is the bot account (`AGENT_USER`) or not an active HD Agent → that row is skipped with an `assignee` note and the next tag / old config decides; the bot is never assigned (Task 2 test `test_unusable_person_is_skipped_with_a_note`).
2. A ticket already assigned (by a person or an Assignment Rule) that carries a tag with a row → the bot still assigns nobody (Task 4 test `test_ticket_already_assigned_is_left_alone`).
3. The ticket's tag differs in case from the row's tag (`ACCOUNTS` vs `Accounts`) → it matches, and the row's spelling is reported (Task 2 test `test_tag_compared_without_case`).
4. Two rows for one tag, category `A` and blank, ticket of category `C` → the blank row; ticket `A` → the `A` row; a row of category `A` alone never serves a `C` ticket (Task 2 tests).
5. A site whose ERP AI Setting has no `tag_assignees` yet (code deployed, migrate not run) → `tag_rules` gives `()` and routing is exactly as before (Task 2 test `test_setting_without_the_table_gives_no_rules`).

---

### Task 1: The table on ERP AI Setting

**Files:**
- Create: `erp_ai/erp_ai_agent/doctype/erp_ai_tag_assignee/__init__.py` (empty), `erp_ai_tag_assignee.json`, `erp_ai_tag_assignee.py` (`class ERPAITagAssignee(Document): pass`, like `erp_ai_user_template.py`)
- Modify: `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` (field + `field_order`), `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` (`validate`, new `check_tag_assignees`), `erp_ai/constants.py`
- Test: `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` (new class `TestTagAssignees`), `erp_ai/tests/test_doctype_descriptions.py`

**Interfaces:**
- Produces: `erp_ai.constants.TAG_ASSIGNEE_DOCTYPE = "ERP AI Tag Assignee"`; child rows with fields `tag` (str), `assignee` (str, HD Agent name = user id), `category` (`""` or `"A"`..`"F"`), reached as `settings.tag_assignees`.

Child DocType JSON (istable, module `ERP AI agent`, `editable_grid: 1`, no section breaks, all three `in_list_view: 1`):

| fieldname | fieldtype | options | label | reqd | description (exact) |
|---|---|---|---|---|---|
| `tag` | Link | Tag | Tag | 1 | `Tag của Helpdesk mà phiếu mang, do người gắn hoặc bot gắn khi phân loại. So không phân biệt hoa thường. Viết Mô tả cho Tag để bot biết khi nào gắn tag này.` |
| `assignee` | Link | HD Agent | Người phụ trách | 1 | `HD Agent nhận phiếu mang tag này và Task C/D của phiếu. Không được là tài khoản agent; người không còn là HD Agent đang hoạt động thì bot bỏ qua dòng này.` |
| `category` | Select | `\nA\nB\nC\nD\nE\nF` | Đầu mục | 0 | `Để trống thì áp cho mọi đầu mục. Dòng có đầu mục của phiếu thắng dòng để trống cùng tag. Một tag và một đầu mục chỉ có một dòng.` |

ERP AI Setting field, placed in `field_order` right after `auto_assign_enabled` and right before `routing_rules`: `tag_assignees`, Table, options `ERP AI Tag Assignee`, label `Gán người theo tag`, description (exact): `Mỗi dòng: một tag, người phụ trách, đầu mục (để trống là mọi đầu mục). Khi Tự gán người bật, bot xét tag người đã gắn trên phiếu rồi tag bot gắn, dòng khớp đầu tiên quyết người nhận phiếu và Task C/D. Không dòng nào khớp thì dùng Quy tắc định tuyến. Dòng trùng tag và đầu mục bị chặn khi lưu.`

- [ ] **Step 1: Set up the branch** — create the worktree and branch (superpowers:using-git-worktrees), move the spec and this plan in, commit `docs(spec): tag-based assignee table in ERP AI Setting (CHG-011)`, create `$SP/wt-test.sh` and `$SP/wt-sync.sh`.

- [ ] **Step 2: Write the failing tests**

In `test_doctype_descriptions.py`: ERP AI Setting `field_count` 82 → 83 (`# CHG-011: tag_assignees (+1)`), `phrases["tag_assignees"] = ("Tự gán người", "Quy tắc định tuyến", "bị chặn khi lưu")`; new `DOCTYPE_CONFIG["ERP AI Tag Assignee"]` with `folder "erp_ai_tag_assignee"`, `field_count 3`, phrases `tag: ("Mô tả", "không phân biệt hoa thường")`, `assignee: ("HD Agent", "tài khoản agent", "bỏ qua")`, `category: ("Để trống", "mọi đầu mục", "thắng")`, `section_count 0`, `read_only_fields ()`, `sections ()`.

In `test_erp_ai_setting.py`, `class TestTagAssignees(FrappeTestCase)`; `setUp` like `TestUserTemplates` (rollback, `keep_agent_settings`, assert the DocType exists), plus `self.person = make_active_agent(self)`, `self.other = make_active_agent(self)` and a Tag `ERPAI-TEST-Kho` (insert if missing). Helper `_save_rows(*rows)` sets `tag_assignees` to `rows` (dicts), saves, returns the stripped error text or `None`.

```python
def test_child_doctype_and_setting_field_shape(self):
	child = json.loads(TAG_ASSIGNEE_JSON.read_text(encoding="utf-8"))
	self.assertEqual(child["istable"], 1)
	fields = {f["fieldname"]: f for f in child["fields"]}
	self.assertEqual(list(fields), ["tag", "assignee", "category"])
	self.assertEqual((fields["tag"]["fieldtype"], fields["tag"]["options"], fields["tag"]["reqd"]), ("Link", "Tag", 1))
	self.assertEqual((fields["assignee"]["options"], fields["assignee"]["reqd"]), ("HD Agent", 1))
	self.assertEqual(fields["category"]["options"], "\nA\nB\nC\nD\nE\nF")
	setting = json.loads(SETTING_JSON.read_text(encoding="utf-8"))
	order = setting["field_order"]
	self.assertEqual(order.index("tag_assignees"), order.index("auto_assign_enabled") + 1)
	self.assertEqual(order.index("routing_rules"), order.index("tag_assignees") + 1)
	(field,) = [f for f in setting["fields"] if f["fieldname"] == "tag_assignees"]
	self.assertEqual((field["fieldtype"], field["options"], field["label"]), ("Table", "ERP AI Tag Assignee", "Gán người theo tag"))

def test_rows_saved_in_order(self):
	self.assertIsNone(self._save_rows({"tag": KHO, "assignee": self.person}, {"tag": KHO, "assignee": self.other, "category": "A"}))
	rows = frappe.get_doc(SETTING_DOCTYPE).tag_assignees
	self.assertEqual([(r.tag, r.assignee, r.category or "") for r in rows], [(KHO, self.person, ""), (KHO, self.other, "A")])

def test_same_tag_and_category_refused(self):
	self.assertEqual(
		self._save_rows({"tag": KHO, "assignee": self.person, "category": "A"}, {"tag": KHO, "assignee": self.other, "category": "A"}),
		"Gán người theo tag dòng 2: trùng với dòng 1",
	)
	self.assertEqual(
		self._save_rows({"tag": KHO, "assignee": self.person}, {"tag": KHO, "assignee": self.other}),
		"Gán người theo tag dòng 2: trùng với dòng 1",
	)

def test_agent_account_refused(self):
	# the bot account is an HD Agent here, so only our check can refuse it (rolled back)
	if not frappe.db.exists("HD Agent", AGENT_USER):
		frappe.get_doc({"doctype": "HD Agent", "user": AGENT_USER, "agent_name": "Bot", "is_active": 1}).insert(ignore_permissions=True)
	self.assertEqual(self._save_rows({"tag": KHO, "assignee": AGENT_USER}), "Gán người theo tag dòng 1: không gán tài khoản agent")
```

- [ ] **Step 3: Run to verify they fail**

Run: `$SP/wt-test.sh $WT erp_ai.tests.test_doctype_descriptions erp_ai.erp_ai_agent.doctype.erp_ai_setting.test_erp_ai_setting`
Expected: FAIL — missing JSON file / field count 82 / DocType missing.

- [ ] **Step 4: Implement** the child DocType files (`creation`/`modified` = now), the Setting field (bump the Setting JSON's `modified` to now so `migrate` picks it up), `TAG_ASSIGNEE_DOCTYPE`, and `ERPAISetting.check_tag_assignees(self)` called in `validate` right after `check_routing_rules()`: first failing row wins, key `(row.tag.casefold(), row.category or "")`, messages `f"Gán người theo tag dòng {row.idx}: trùng với dòng {seen[key]}"` and `f"Gán người theo tag dòng {row.idx}: không gán tài khoản agent"` (agent check first).

- [ ] **Step 5: Sync the DocTypes onto miyano**

Run: `$SP/wt-sync.sh $WT`, then `bench --site miyano mariadb -e "select count(*) from \`tabDocField\` where parent='ERP AI Setting' and fieldname='tag_assignees'"` from `/home/miyano/frappe-bench`.
Expected: `1`.

- [ ] **Step 6: Run to verify they pass** (same command as Step 3). Expected: OK.

- [ ] **Step 7: Commit** — `feat(settings): table of tag → person on ERP AI Setting (CHG-011)`.

---

### Task 2: Routing picks the person by tag

**Files:**
- Modify: `erp_ai/agent/routing.py` (`RouteDecision`, `decide_route`, new `TagRule`, `tag_rules`, `_tag_assignee`)
- Test: `erp_ai/agent/test_routing.py` (new classes `TestDecideAssigneeByTag`, `TestTagRules`)

**Interfaces:**
- Consumes: child rows of Task 1 (`tag`, `assignee`, `category`).
- Produces:
  - `class TagRule(NamedTuple): tag: str; assignee: str; category: str` (category `""` = every category).
  - `tag_rules(settings) -> tuple[TagRule, ...]`: rows of `settings.get("tag_assignees") or ()` in order, `category or ""`, rows with a blank tag or assignee left out.
  - `RouteDecision.assignee_tag: str | None = None` (last field, default None): the row's tag spelling when the table chose the assignee.
  - `decide_route(..., tags: tuple[str, ...] = (), tag_rules: tuple[TagRule, ...] = ())` (keyword-only, after `now`).

- [ ] **Step 1: Write the failing tests**

```python
TAG_RULES = (
	routing.TagRule("Accounts", "hieu@x.com", ""),
	routing.TagRule("tracecore", "e2e@x.com", ""),
	routing.TagRule("Accounts", "acc.a@x.com", "A"),
)

def _decide_by_tags(category, tags, rules=TAG_RULES, is_active_agent=None, department=None):
	return routing.decide_route(
		Classification(category=category, confidence="Cao", importance=1, department=department),
		"Thông thường", DEFAULT_CATEGORY_MAPPING, ASSIGN_CONFIG,
		team_exists=lambda team: True, is_excluded_team=lambda team: False,
		is_active_agent=is_active_agent or (lambda user: True),
		tags=tags, tag_rules=rules,
	)

class TestDecideAssigneeByTag(FrappeTestCase):
	def test_first_tag_with_a_row_decides(self):
		d = _decide_by_tags("C", ("Stock", "tracecore", "Accounts"))
		self.assertEqual((d.assignee, d.assignee_tag), ("e2e@x.com", "tracecore"))

	def test_tag_compared_without_case(self):
		d = _decide_by_tags("C", ("ACCOUNTS",))
		self.assertEqual((d.assignee, d.assignee_tag), ("hieu@x.com", "Accounts"))

	def test_row_of_the_ticket_category_beats_blank_row(self):
		self.assertEqual(_decide_by_tags("A", ("Accounts",)).assignee, "acc.a@x.com")
		self.assertEqual(_decide_by_tags("C", ("Accounts",)).assignee, "hieu@x.com")

	def test_row_of_another_category_is_not_used(self):
		d = _decide_by_tags("C", ("Accounts",), (routing.TagRule("Accounts", "acc.a@x.com", "A"),))
		self.assertEqual((d.assignee, d.assignee_tag), ("c.default@x.com", None))

	def test_no_matching_tag_falls_back_to_routing_rules(self):
		d = _decide_by_tags("B", ("Stock",))
		self.assertEqual((d.assignee, d.assignee_tag), ("b.default@x.com", None))
		self.assertEqual(_assignee_notes(d), [])

	def test_no_tags_or_no_rules_change_nothing(self):
		self.assertEqual(_decide_by_tags("A", ()).assignee, "a.default@x.com")
		self.assertEqual(_decide_by_tags("A", ("Accounts",), ()).assignee, "a.default@x.com")

	def test_tag_row_beats_department_head_for_d_and_e(self):
		for category in "DE":
			with self.subTest(category=category):
				d = _decide_by_tags(category, ("Accounts",), department="Kế toán")
				self.assertEqual((d.assignee, d.assignee_tag), ("hieu@x.com", "Accounts"))

	def test_unusable_person_is_skipped_with_a_note(self):
		d = _decide_by_tags("C", ("tracecore", "Accounts"), is_active_agent=lambda user: user != "e2e@x.com")
		self.assertEqual((d.assignee, d.assignee_tag), ("hieu@x.com", "Accounts"))
		self.assertEqual(_assignee_notes(d), ["tag tracecore: e2e@x.com không phải HD Agent đang hoạt động"])
		d = _decide_by_tags("C", ("tracecore",), (routing.TagRule("tracecore", AGENT_USER, ""),))
		self.assertEqual((d.assignee, d.assignee_tag), ("c.default@x.com", None))
		self.assertEqual(_assignee_notes(d), ["tag tracecore: không gán tài khoản agent"])

	def test_task_follows_the_tag_person(self):
		self.assertTrue(_decide_by_tags("C", ("tracecore",)).needs_task)

class TestTagRules(FrappeTestCase):
	def test_rows_read_in_order_blank_ones_left_out(self):
		settings = frappe._dict(tag_assignees=[
			frappe._dict(tag="Accounts", assignee="hieu@x.com", category=None),
			frappe._dict(tag="", assignee="x@x.com", category="A"),
			frappe._dict(tag="tracecore", assignee="e2e@x.com", category="C"),
		])
		self.assertEqual(routing.tag_rules(settings), (
			routing.TagRule("Accounts", "hieu@x.com", ""), routing.TagRule("tracecore", "e2e@x.com", "C"),
		))

	def test_setting_without_the_table_gives_no_rules(self):
		self.assertEqual(routing.tag_rules(frappe._dict()), ())
```

- [ ] **Step 2: Run to verify they fail**

Run: `$SP/wt-test.sh $WT erp_ai.agent.test_routing`
Expected: FAIL — `module 'erp_ai.agent.routing' has no attribute 'TagRule'`.

- [ ] **Step 3: Implement** in `routing.py`. `_tag_assignee(category, tags, rules, is_active_agent, notes) -> tuple[str, str] | None` goes through `tags` in order, each tag once (casefold); for a tag, the candidate rows are those whose tag matches without case and whose category is the ticket's, then those with a blank category; the first candidate whose person is not `AGENT_USER` (compare like `_assignee`) and passes `is_active_agent` gives `(row.assignee, row.tag)`; a refused candidate adds `{"field": "assignee", "reason": f"tag {row.tag}: không gán tài khoản agent"}` or `f"tag {row.tag}: {row.assignee} không phải HD Agent đang hoạt động"` and the search goes on. In `decide_route`, call it before `_assignee`; only when it gives `None` does `_assignee` run (so its "cấu hình không có người" note appears only then).

- [ ] **Step 4: Run to verify they pass** (same command). Expected: OK, the existing `TestDecideAssignee` cases still green.

- [ ] **Step 5: Commit** — `feat(routing): the first ticket tag with a row in the table decides the person (CHG-011)`.

---

### Task 3: The table's tags are always in the classify label catalog

**Files:**
- Modify: `erp_ai/agent/labels.py` (`classify_inputs`)
- Test: `erp_ai/agent/test_labels.py` (`TestClassifyInputs`)

**Interfaces:**
- Produces: `classify_inputs(ticket_name: str, subject: str, description: str, pinned: tuple[str, ...] = ()) -> LabelInputs`. `label_catalog` = the top `CATALOG_MAX` as today, then each pinned tag not already in it (casefold), in `pinned` order, as `(tag, tickets carrying it, Tag description)`; pinned tags are never cut by `CATALOG_MAX`.

- [ ] **Step 1: Write the failing tests** (Tags made through a helper that inserts `{"doctype": "Tag", "name": name, "description": ...}` when missing)

```python
def test_pinned_tag_without_tickets_is_listed_with_its_description(self):
	current = self._ticket("c")
	pinned = self._tag(f"{PREFIX}Ghim", "Phiếu về Tracecore")
	self.assertIn((pinned, 0, "Phiếu về Tracecore"), labels.classify_inputs(current, "c", "<p>x</p>", pinned=(pinned,)).label_catalog)

def test_pinned_tag_in_use_is_listed_once_with_its_count(self):
	self._ticket("a", KHO)
	current = self._ticket("c")
	self.assertEqual(self._ours(labels.classify_inputs(current, "c", "<p>x</p>", pinned=(KHO,)).label_catalog), [(KHO, 1, "")])

def test_pinned_tags_kept_when_the_catalog_is_full(self):
	current = self._ticket("c")
	self._ticket("a", *[f"{PREFIX}n{index:02d}" for index in range(labels.CATALOG_MAX + 2)])
	pinned = self._tag(f"{PREFIX}zz", "")
	catalog = labels.classify_inputs(current, "c", "<p>x</p>", pinned=(pinned,)).label_catalog
	self.assertEqual(catalog[-1], (pinned, 0, ""))
	self.assertEqual(len(catalog), labels.CATALOG_MAX + 1)
```

- [ ] **Step 2: Run to verify they fail** — `$SP/wt-test.sh $WT erp_ai.agent.test_labels`. Expected: FAIL — `unexpected keyword argument 'pinned'`.

- [ ] **Step 3: Implement** `pinned` in `classify_inputs` (one `Tag` description read for the top and the pinned names together).

- [ ] **Step 4: Run to verify they pass** (same command). Expected: OK.

- [ ] **Step 5: Commit** — `feat(labels): the tags of the assignee table always reach the label catalog (CHG-011)`.

---

### Task 4: The runner routes by tag and says so

**Files:**
- Modify: `erp_ai/agent/runner.py` (`_classify`, `_label_inputs`, `_assign_unit`, `_route_lines`, `_route`, new constant `ROUTE_ASSIGNED_BY_TAG`)
- Modify: `erp_ai/test_utils.py` (new `make_tag`, `set_tag_assignees`)
- Test: `erp_ai/agent/test_runner_routing.py` (new constant `CLASSIFY_TAGGED`, new class `TestRoutingAssignByTag(AssignTestBase)`)

**Interfaces:**
- Consumes: `routing.tag_rules`, `decide_route(tags=, tag_rules=)`, `RouteDecision.assignee_tag` (Task 2); `classify_inputs(pinned=)` (Task 3); `TAG_ASSIGNEE_DOCTYPE` (Task 1).
- Produces:
  - `runner.ROUTE_ASSIGNED_BY_TAG = "Đã gán cho {person} (theo tag {tag})."`
  - `test_utils.make_tag(name: str, description: str = "") -> str` (inserts the Tag when missing, returns the name).
  - `test_utils.set_tag_assignees(*rows: tuple[str, str, str]) -> None`: replaces the Setting's `tag_assignees` rows in the DB without validation (`parent`/`parenttype` `ERP AI Setting`, `parentfield` `tag_assignees`, `idx` from 1); `keep_agent_settings` restores them.

- [ ] **Step 1: Write the failing tests**

`CLASSIFY_TAGGED` = `CLASSIFY_SCORED`'s object plus `"nhan": [TAG_KHO]`, with `TAG_KHO = f"{PREFIX}Kho"` and `TAG_KE_TOAN = f"{PREFIX}Ke toan"`.

```python
class TestRoutingAssignByTag(AssignTestBase):
	def setUp(self):
		super().setUp()
		self.tag_person = make_active_agent(self)
		make_tag(TAG_KHO)
		set_tag_assignees((TAG_KHO, self.tag_person, ""))
		self.gateway.results = [make_model_result(text=CLASSIFY_TAGGED), make_model_result(stop_reason="end_turn")]

	def test_model_label_with_a_row_gives_the_ticket_to_its_person(self):
		self._run()
		self.assertEqual(self._assigned_to(), [self.tag_person])
		(action,) = self._action("assign_owner")
		self.assertEqual((action["name"], action["ok"], action.get("rule")), (self.tag_person, True, f"tag:{TAG_KHO}"))
		self.assertIn(runner.ROUTE_ASSIGNED_BY_TAG.format(person=get_fullname(self.tag_person), tag=TAG_KHO), self._comment_text())
		self.assertEqual(self._single_entry().predicted_assignee, self.tag_person)

	def test_tag_a_person_put_on_the_ticket_comes_before_the_model_label(self):
		other = make_active_agent(self)
		make_tag(TAG_KE_TOAN)
		set_tag_assignees((TAG_KHO, self.tag_person, ""), (TAG_KE_TOAN, other, ""))
		frappe.get_doc("HD Ticket", self.ticket.name).add_tag(TAG_KE_TOAN)
		self._run()
		self.assertEqual(self._assigned_to(), [other])

	def test_no_row_for_the_labels_keeps_the_configured_default(self):
		set_tag_assignees()
		self._run()
		self.assertEqual(self._assigned_to(), [self.person])
		self.assertIn(runner.ROUTE_ASSIGNED.format(person=get_fullname(self.person)), self._comment_text())
		(action,) = self._action("assign_owner")
		self.assertFalse(action.get("rule"))

	def test_ticket_already_assigned_is_left_alone(self):
		assign_to.add({"assign_to": [self.person], "doctype": "HD Ticket", "name": self.ticket.name})
		self._run()
		self.assertEqual(self._assigned_to(), [self.person])

	def test_table_tags_reach_the_classify_request(self):
		self._run()
		classify = next(call for call in self.gateway.calls if call["task"] == "classify")
		self.assertIn(f"- {TAG_KHO} (0 phiếu)", classify["messages"][0]["content"])
```

- [ ] **Step 2: Run to verify they fail** — `$SP/wt-test.sh $WT erp_ai.agent.test_runner_routing`. Expected: FAIL — `cannot import name 'make_tag'` (then, once the helpers exist, the default person assigned instead of the tag person).

- [ ] **Step 3: Implement**
  - `_classify`: read `_user_tags` with the ticket; `rules = routing.tag_rules(settings)`; `_label_inputs(..., pinned=tuple(dict.fromkeys(rule.tag for rule in rules)))` (new keyword with default `()`, passed on to `classify_inputs`); `decide_route(..., tags=(*ticket_labels.parse_tags(ticket._user_tags), *classification.labels), tag_rules=rules)`.
  - `_assign_unit`: the success action gets `rule=f"tag:{decision.assignee_tag}"` when `decision.assignee_tag`, else as today.
  - `_route_lines(result, assigned, task, watcher, labelled=(), assigned_tag=None)`: `ROUTE_ASSIGNED_BY_TAG.format(person=..., tag=assigned_tag)` when `assigned_tag`, else `ROUTE_ASSIGNED` as today; `_route` passes `decision.assignee_tag`.

- [ ] **Step 4: Run to verify they pass** (same command). Expected: OK, all existing routing cases still green.

- [ ] **Step 5: Run every touched and neighbouring module**

Run: `$SP/wt-test.sh $WT erp_ai.agent.test_routing erp_ai.agent.test_labels erp_ai.agent.test_runner_routing erp_ai.agent.test_agent_runner erp_ai.agent.tools.test_write_ticket erp_ai.agent.tools.test_registry erp_ai.eval.test_run_eval erp_ai.tests.test_doctype_descriptions erp_ai.tests.test_architecture erp_ai.erp_ai_agent.doctype.erp_ai_setting.test_erp_ai_setting`
Expected: every module OK. A failure is fixed here or reported, never skipped.

- [ ] **Step 6: Commit** — `feat(runner): route by the tag table and name the tag in the comment and the log (CHG-011)`.

---

## After the branch (for the person, not a task)

- Merge `team/CHG-011` into `develop` when the review is done (ask first).
- Local site `miyano`: `bench --site miyano migrate` under the site lock (creates the table for good), then restart web and workers (`kill -TERM` per memory note, no sudo).
- Fill the table in ERP AI Setting (e.g. `Accounts` → Hiếu, `tracecore` → e2e) and write a Mô tả on each Tag.
- Prod `erp.miyano.com.vn`: only with human approval.
