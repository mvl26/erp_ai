import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from unittest.mock import patch

import frappe
from frappe.permissions import AUTOMATIC_ROLES
from frappe.utils import get_bench_path
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent.run_log import write_entry
from erp_ai.agent.tools.change_guard import FileOp
from erp_ai.constants import (
	AGENT_STATUS_EVENT,
	AGENT_USER,
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_OP_CREATE,
	CHANGE_OP_DELETE,
	CHANGE_OP_RENAME,
	CHANGE_STATUS_PENDING,
	CORE_APPS,
	HELPDESK_AGENT_ROLE,
	LESSON_DOCTYPE,
	LESSON_EVENT_DOCTYPE,
	OPERATION_DOCTYPE,
	PROPOSAL_DOCTYPE,
	ROLE_AGENT,
	SETTING_DOCTYPE,
)
from erp_ai.gateway import GatewayError, ModelResult


def make_model_result(**kw) -> ModelResult:
	fields = {
		"content": [],
		"text": "",
		"stop_reason": "end_turn",
		"model": "fake-model",
		"usage": {
			"input_tokens": 0,
			"output_tokens": 0,
			"cache_creation_input_tokens": 0,
			"cache_read_input_tokens": 0,
		},
		"cost_usd": 0.0,
		"credential_label": "fake",
		"keys_tried": [],
		"latency_ms": 0,
		"request_id": "req_fake",
	}
	fields.update(kw)
	return ModelResult(**fields)


class FakeGateway:
	"""Thay `erp_ai.gateway.call_model`: trả lần lượt các kết quả đã xếp, ném nếu là GatewayError.

	`on_call(task, kwargs)` chạy trước khi trả kết quả (ghi thứ tự lời gọi, đẩy đồng hồ giả).
	"""

	def __init__(self, *results, on_call=None):
		self.results = list(results)
		self.on_call = on_call
		self.calls = []

	@property
	def call_count(self) -> int:
		return len(self.calls)

	def __call__(self, task, **kwargs):
		self.calls.append({"task": task, **kwargs})
		if self.on_call is not None:
			self.on_call(task, kwargs)
		result = self.results.pop(0) if self.results else make_model_result()
		if isinstance(result, GatewayError):
			raise result
		return result


def record_status_signals(testcase) -> list[dict]:
	"""Patch `frappe.realtime.emit_via_redis`; return the list that collects `{"event", "message", "room"}` of every agent status signal.

	Other events are dropped, so nothing reaches Redis. The patch is removed by `addCleanup`.
	"""
	signals = []

	def record(event, message, room=None):
		if event == AGENT_STATUS_EVENT:
			signals.append({"event": event, "message": message, "room": room})

	emit_patch = patch("frappe.realtime.emit_via_redis", side_effect=record)
	emit_patch.start()
	testcase.addCleanup(emit_patch.stop)
	return signals


def set_agent_settings(**fields) -> None:
	"""Set ERP AI Setting values directly in the DB (no validate), for tests."""
	for fieldname, value in fields.items():
		frappe.db.set_single_value(SETTING_DOCTYPE, fieldname, value)


def clear_lesson_store() -> None:
	"""Delete every ERP AI Lesson and ERP AI Lesson Event row inside the current transaction, so a test sees only the
	lessons it makes, whatever the shared site holds (NFR-7). Never commits: the test's rollback brings the rows back.
	"""
	frappe.db.delete(LESSON_EVENT_DOCTYPE)
	frappe.db.delete(LESSON_DOCTYPE)


def keep_agent_settings(testcase) -> None:
	"""Snapshot ERP AI Setting (its `tabSingles` rows, the rows of its child tables and their `__Auth` rows);
	`addCleanup` puts them back.

	`__Auth` values are copied as stored (encrypted), never decrypted. The restore writes in the current
	transaction and never commits (NFR-7).
	"""
	singles = frappe.db.sql(
		"select field, value from `tabSingles` where doctype=%s", SETTING_DOCTYPE, as_dict=True
	)
	child_doctypes = sorted({field.options for field in frappe.get_meta(SETTING_DOCTYPE).get_table_fields()})
	child_rows = {
		child: frappe.get_all(
			child,
			filters={"parent": SETTING_DOCTYPE, "parenttype": SETTING_DOCTYPE},
			fields=["*"],
			order_by="name",
		)
		for child in child_doctypes
	}
	auth_doctypes = [SETTING_DOCTYPE, *child_doctypes]
	auth_rows = frappe.db.sql(
		"select doctype, name, fieldname, password, encrypted from `__Auth` where doctype in %(doctypes)s",
		{"doctypes": tuple(auth_doctypes)},
		as_dict=True,
	)

	def restore():
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE})
		for row in singles:
			frappe.db.sql(
				"insert into `tabSingles` (doctype, field, value) values (%s, %s, %s)",
				(SETTING_DOCTYPE, row.field, row.value),
			)
		for child, rows in child_rows.items():
			frappe.db.delete(child, {"parent": SETTING_DOCTYPE, "parenttype": SETTING_DOCTYPE})
			for row in rows:
				frappe.get_doc({**row, "doctype": child}).db_insert()
		frappe.db.delete("__Auth", {"doctype": ("in", auth_doctypes)})
		for row in auth_rows:
			frappe.db.sql(
				"insert into `__Auth` (doctype, name, fieldname, password, encrypted) values (%s, %s, %s, %s, %s)",
				(row.doctype, row.name, row.fieldname, row.password, row.encrypted),
			)

	# Registered before `restore` so it runs after it, and still runs when `restore` fails.
	testcase.addCleanup(frappe.db.value_cache.pop, SETTING_DOCTYPE, None)
	testcase.addCleanup(frappe.clear_document_cache, SETTING_DOCTYPE, SETTING_DOCTYPE)
	testcase.addCleanup(restore)


def add_credential(label, **fields) -> str:
	"""Append a key row to ERP AI Setting without validation and return the child row name."""
	settings = frappe.get_single(SETTING_DOCTYPE)
	settings.append("credentials", {"label": label, "api_key": f"sk-{label}", **fields})
	settings.flags.ignore_validate = True
	settings.save(ignore_permissions=True)
	return settings.credentials[-1].name


class _FakeRawResponse:
	def __init__(self, message, headers, request_id):
		self._message = message
		self.headers = headers
		self.request_id = request_id

	def parse(self):
		return _FakeMessage(self._message, self.request_id)


class _FakeMessage:
	def __init__(self, message, request_id):
		self._message = message
		self._request_id = request_id

	def model_dump(self) -> dict:
		return dict(self._message)


class _FakeRawMessages:
	def __init__(self, owner):
		self._owner = owner

	def create(self, **request):
		self._owner.requests.append(request)
		if self._owner.error is not None:
			raise self._owner.error
		return _FakeRawResponse(self._owner.message, self._owner.headers, self._owner.request_id)


class _FakeMessages:
	def __init__(self, owner):
		self.with_raw_response = _FakeRawMessages(owner)


class FakeAnthropicClient:
	"""Thay `anthropic.Anthropic` trong test: không mạng, ghi lại mọi `messages.create(**request)`."""

	def __init__(self, message=None, headers=None, request_id="req_fake", error=None):
		self.message = message if message is not None else {"type": "message", "content": []}
		self.headers = headers or {}
		self.request_id = request_id
		self.error = error
		self.requests = []
		self.messages = _FakeMessages(self)


def fake_anthropic_client(**kwargs) -> FakeAnthropicClient:
	return FakeAnthropicClient(**kwargs)


def make_log_entry(**fields) -> str:
	"""Write an ERP AI Log row through `run_log.write_entry` (current session user must be allowed) and return its name."""
	values = {"run_id": "ERPAI-TEST-run", "entry_type": "skip", "trigger": "ticket_insert", "turn": 0}
	values.update(fields)
	return write_entry(**values)


PREFIX = "ERPAI-TEST-"
PINNED_AGENT_ROLES = (ROLE_AGENT, HELPDESK_AGENT_ROLE)
SLA_RESPONSE_HOURS_BY_PRIORITY = {"Low": 4, "Medium": 3, "High": 2, "Urgent": 1}
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _agent_role_rows() -> list[dict]:
	return frappe.get_all(
		"Has Role",
		filters={"parent": AGENT_USER, "parenttype": "User"},
		fields=["*"],
		order_by="creation, name",
	)


def pin_agent_roles(testcase) -> None:
	"""Pin the agent account's Has Role set to exactly {ERP AI Agent, Agent} (plus automatic roles) for one test.

	`addCleanup` puts back the exact rows that were there. Call it
	after `testcase.addCleanup(frappe.db.rollback)` so the restore runs first (cleanups run last-in first-out).
	"""
	rows = _agent_role_rows()
	if not frappe.db.exists("User", AGENT_USER):
		raise AssertionError(f"{AGENT_USER} does not exist on this site")

	def restore():
		frappe.db.delete("Has Role", {"parent": AGENT_USER, "parenttype": "User"})
		for row in rows:
			frappe.get_doc({**row, "doctype": "Has Role"}).db_insert()

	# Registered before `restore` so it runs after it, and still runs when `restore` fails.
	testcase.addCleanup(frappe.clear_cache, user=AGENT_USER)
	testcase.addCleanup(restore)

	keep = set(PINNED_AGENT_ROLES) | set(AUTOMATIC_ROLES)
	frappe.db.delete("Has Role", {"parent": AGENT_USER, "parenttype": "User", "role": ("not in", list(keep))})
	present = {row["role"] for row in rows}
	for role in PINNED_AGENT_ROLES:
		if role not in present:
			frappe.get_doc(
				{
					"doctype": "Has Role",
					"parent": AGENT_USER,
					"parenttype": "User",
					"parentfield": "roles",
					"role": role,
				}
			).db_insert()
	frappe.clear_cache(user=AGENT_USER)


def make_routing_rules(**overrides) -> str:
	"""JSON of `routing_rules` in the design 3.3 shape, with no people filled in; `overrides` replace top-level keys."""
	rules = {
		"assignees": {cat: {"default": "", "prefixes": {}} for cat in "ABCF"},
		"departments": {},
		"importance_priority": {"1": "", "2": "High", "3": "High"},
		"expected_sla": {
			"A": {"response_min": 15, "resolution_min": 480},
			"B": {"response_min": 15, "resolution_min": 240},
			"C": {"response_min": 60, "resolution_min": 1440},
			"D": {"response_min": 60, "resolution_min": None},
			"E": {"response_min": 60, "resolution_min": None},
			"F": {"response_min": 5, "resolution_min": 60},
		},
	}
	rules.update(overrides)
	return json.dumps(rules, ensure_ascii=False)


def _unique(label: str) -> str:
	return f"{PREFIX}{label}-{frappe.generate_hash(length=8)}"


def make_sla(testcase, *, condition: str = "", default: bool = False, enabled: bool = True) -> str:
	"""Insert a self-made HD Service Level Agreement (own holiday list) and return its name. Rolled back by the test."""
	holiday_list = frappe.get_doc(
		{
			"doctype": "HD Service Holiday List",
			"holiday_list_name": _unique("Holidays"),
			"from_date": "2020-01-01",
			"to_date": "2099-12-31",
		}
	).insert(ignore_permissions=True)
	sla = frappe.get_doc(
		{
			"doctype": "HD Service Level Agreement",
			"service_level": _unique("SLA"),
			"holiday_list": holiday_list.name,
			"condition": condition,
			"default_sla": 1 if default else 0,
			"enabled": 1 if enabled else 0,
			"apply_sla_for_resolution": 1,
			"support_and_resolution": [
				{"workday": day, "start_time": "00:00:00", "end_time": "23:59:00"} for day in WEEKDAYS
			],
			"priorities": [
				{
					"priority": priority,
					"default_priority": 1 if priority == "Medium" else 0,
					"response_time": 3600 * hours,
					"resolution_time": 4 * 3600 * hours,
				}
				for priority, hours in SLA_RESPONSE_HOURS_BY_PRIORITY.items()
			],
		}
	)
	sla.insert(ignore_permissions=True)
	return sla.name


def make_active_agent(testcase) -> str:
	"""Create a user with the Agent role and an active HD Agent row; return the user ID. Rolled back by the test."""
	email = f"{_unique('agent').lower()}@example.com"
	create_agent(email)
	return email


def make_team(testcase, *, with_rule: bool = False, rule_users: tuple[str, ...] = ()) -> str:
	"""Insert a self-made HD Team and return its name.

	Helpdesk always creates an Assignment Rule for a new team; `with_rule=False` removes it again, so the team
	has none. `rule_users` are the members (and rule users); empty means one fresh active agent.
	"""
	members = tuple(rule_users) or (make_active_agent(testcase),)
	team = frappe.get_doc(
		{"doctype": "HD Team", "team_name": _unique("Team"), "users": [{"user": user} for user in members]}
	).insert(ignore_permissions=True)
	if not with_rule:
		rule = team.assignment_rule
		frappe.db.set_value("HD Team", team.name, "assignment_rule", None, update_modified=False)
		frappe.delete_doc("Assignment Rule", rule, force=True, ignore_permissions=True)
	return team.name


SOURCE_ROOT_PATH = "erp_ai.agent.tools.source.get_source_root"


class TempAppsRoot:
	"""A temporary `apps/` root that `source.get_source_root` returns for one test; the real `apps/` is never touched.

	Layout under `base` (a fresh `tempfile.mkdtemp()`, removed by `addCleanup`):
	`apps/<app>/ok.py`, `.env`, `x.pem`, `site_config.json` for every app in `apps`; in the first app
	`link_out.py` (symlink to `outside/plain.py`) and `dir_out` (symlink to `outside/`); `outside/plain.py`
	and `sites/site_config.json` sit next to `apps/`, outside the root.
	"""

	def __init__(self, testcase, apps=("myapp",)):
		self.base = os.path.realpath(tempfile.mkdtemp())
		testcase.addCleanup(shutil.rmtree, self.base, True)
		self.root = os.path.join(self.base, "apps")
		self.outside = os.path.join(self.base, "outside")
		os.makedirs(self.root)
		self.write("plain.py", "x = 1\n", root=self.outside)
		self.write("site_config.json", "{}\n", root=os.path.join(self.base, "sites"))
		for app in apps:
			for name in ("ok.py", ".env", "x.pem", "site_config.json"):
				self.write(os.path.join(app, name), "x = 1\n")
		if apps:
			os.symlink(
				os.path.join(self.outside, "plain.py"), os.path.join(self.root, apps[0], "link_out.py")
			)
			os.symlink(self.outside, os.path.join(self.root, apps[0], "dir_out"))
		patcher = patch(SOURCE_ROOT_PATH, return_value=self.root)
		patcher.start()
		testcase.addCleanup(patcher.stop)

	def write(self, rel, text, root=None) -> str:
		"""Write `text` to `rel` under `root` (default: the temp `apps/`), creating parents; return the full path."""
		path = os.path.join(root or self.root, rel)
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, "w", encoding="utf-8") as handle:
			handle.write(text)
		return path


GIT_SANDBOX_NAME = "ERP AI Test"
GIT_SANDBOX_EMAIL = "erp-ai-test@sandbox.invalid"
GIT_SANDBOX_TIMEOUT_S = 30
GIT_SANDBOX_REMOTE_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
IN_PROGRESS_KINDS = ("MERGE_HEAD", "rebase-merge", "CHERRY_PICK_HEAD", "REVERT_HEAD")
MARKER_HOOKS = (
	"pre-commit",
	"prepare-commit-msg",
	"commit-msg",
	"post-commit",
	"post-index-change",
	"reference-transaction",
)


class GitSandbox:
	"""A temporary `apps/` root of throw-away git repos that `source.get_source_root` returns for one test (NFR-9).

	Every app in `apps` is a repo on branch `main` with one first commit (`README.md`). When `erp_ai` is in
	`apps` and `erp_ai_worktree` is set, `<root>/<erp_ai_worktree>` is a real `git worktree` of it on a branch
	of the same name. The helper runs git only inside its own `tempfile.mkdtemp()` directory (removed by
	`addCleanup`), with inherited `GIT_*` variables dropped, no global/system config and a fixed test identity.
	"""

	def __init__(
		self,
		testcase,
		apps=("frappe", "erpnext", "helpdesk", "hrms", "erp_ai", "custom_app"),
		*,
		erp_ai_worktree="erp_ai-wt",
	):
		self.base = os.path.realpath(tempfile.mkdtemp())
		testcase.addCleanup(shutil.rmtree, self.base, True)
		self.root = os.path.join(self.base, "apps")
		self.no_hooks = os.path.join(self.base, "no-hooks")
		os.makedirs(self.root)
		os.makedirs(self.no_hooks)
		for app in apps:
			os.makedirs(self.repo(app))
			self.git(app, "init", "--quiet", "--initial-branch=main")
			self.commit_file(app, "README.md", f"# {app}\n", message="initial commit")
		if erp_ai_worktree and "erp_ai" in apps:
			self.git(
				"erp_ai", "worktree", "add", "--quiet", "-b", erp_ai_worktree, self.repo(erp_ai_worktree)
			)
		patcher = patch(SOURCE_ROOT_PATH, return_value=self.root)
		patcher.start()
		testcase.addCleanup(patcher.stop)

	def env(self) -> dict:
		"""Environment of every helper git command: the process env minus `GIT_*`, plus isolation and identity."""
		env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
		env.update(
			{
				"GIT_CONFIG_GLOBAL": "/dev/null",
				"GIT_CONFIG_NOSYSTEM": "1",
				"GIT_CEILING_DIRECTORIES": self.root,
				"GIT_AUTHOR_NAME": GIT_SANDBOX_NAME,
				"GIT_AUTHOR_EMAIL": GIT_SANDBOX_EMAIL,
				"GIT_COMMITTER_NAME": GIT_SANDBOX_NAME,
				"GIT_COMMITTER_EMAIL": GIT_SANDBOX_EMAIL,
				"LC_ALL": "C",
			}
		)
		return env

	def repo(self, app) -> str:
		return os.path.join(self.root, app)

	def _repo_dir(self, app) -> str:
		"""Real path of `repo(app)`; refuse the root itself, anything outside it and a missing directory."""
		path = os.path.realpath(self.repo(app))
		if os.path.commonpath([self.root, path]) != self.root or path == self.root:
			raise ValueError(f"GitSandbox refuses to work outside the repos under {self.root}: {path}")
		if not os.path.isdir(path):
			raise ValueError(f"GitSandbox has no repo {app}: {path}")
		return path

	def git(self, app, *args, run_hooks=False) -> str:
		"""Run `git <args>` in `repo(app)` and return stdout; refuse any directory outside the sandbox repos.

		Repo hooks run only with `run_hooks=True`; otherwise `core.hooksPath` is an empty temp dir.
		"""
		cwd = self._repo_dir(app)
		hooks = () if run_hooks else ("-c", f"core.hooksPath={self.no_hooks}")
		completed = subprocess.run(
			["git", *hooks, *args],
			cwd=cwd,
			env=self.env(),
			stdin=subprocess.DEVNULL,
			capture_output=True,
			text=True,
			timeout=GIT_SANDBOX_TIMEOUT_S,
		)
		if completed.returncode != 0:
			raise AssertionError(f"git {' '.join(args)} failed in {cwd}: {completed.stderr}")
		return completed.stdout

	def _write(self, app, rel, content) -> None:
		"""Write `content` to `rel` of `repo(app)`; refuse an `app` or a `rel` that resolves outside that repo."""
		repo = self._repo_dir(app)
		path = os.path.realpath(os.path.join(repo, rel))
		if os.path.commonpath([repo, path]) != repo or path == repo:
			raise ValueError(f"GitSandbox refuses to write outside {repo}: {rel!r}")
		self._write_file(path, content)

	@staticmethod
	def _write_file(path, content) -> None:
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, "wb") as handle:
			handle.write(content if isinstance(content, bytes) else content.encode("utf-8"))

	def commit_file(self, app, rel, content, *, message=None, run_hooks=False) -> str:
		"""Write, add and commit one file; return the new commit sha. Repo hooks run only with `run_hooks`."""
		self._write(app, rel, content)
		self.git(app, "add", "--", rel, run_hooks=run_hooks)
		self.git(
			app,
			"commit",
			"--quiet",
			"--no-gpg-sign",
			"-m",
			message or f"add {rel}",
			"--",
			rel,
			run_hooks=run_hooks,
		)
		return self.git(app, "rev-parse", "HEAD").strip()

	def stage(self, app, rel, content) -> None:
		self._write(app, rel, content)
		self.git(app, "add", "--", rel)

	def write_unstaged(self, app, rel, content) -> None:
		self._write(app, rel, content)

	def refs(self, app) -> dict:
		"""`{refname: sha}` of every ref (`for-each-ref`)."""
		output = self.git(app, "for-each-ref", "--format=%(refname) %(objectname)")
		return dict(line.split(" ", 1) for line in output.splitlines())

	def log_meta(self, app, rev="HEAD") -> str:
		"""Author name, author email, committer name, committer email and message of `rev`, one per line."""
		return self.git(app, "log", "-1", "--format=format:%an%n%ae%n%cn%n%ce%n%B", rev)

	def _git_path(self, app, name) -> str:
		"""Absolute `git rev-parse --git-path <name>` of `app` (a worktree gets its own admin dir)."""
		return self.git(app, "rev-parse", "--path-format=absolute", "--git-path", name).strip()

	def remote_dir(self, app, name="origin") -> str:
		"""The temp bare repo behind remote `name` of `app`; it lives under `base`, outside `root`.

		`name` is one path component (`GIT_SANDBOX_REMOTE_NAME`), so the repo cannot leave `base`.
		"""
		if not GIT_SANDBOX_REMOTE_NAME.fullmatch(name):
			raise ValueError(f"GitSandbox refuses remote name {name!r}")
		return os.path.join(self.base, "remotes", app, f"{name}.git")

	def add_remote(self, app, name="origin", url="https://x-token-FAKE@host/r.git", ahead=2) -> None:
		"""Make `name/<branch>` the upstream of the checked-out branch, `ahead` local commits behind HEAD.

		The remote is a temp bare repo filled by path; only the fake `url` is written to `.git/config`.
		"""
		if ahead < 0:
			raise ValueError(f"ahead must be >= 0: {ahead}")
		bare = self.remote_dir(app, name)
		branch = self.git(app, "symbolic-ref", "--short", "HEAD").strip()
		self.git(app, "init", "--quiet", "--bare", bare)
		self.git(app, "push", "--quiet", bare, f"HEAD:refs/heads/{branch}")
		self.git(app, "remote", "add", name, url)
		self.git(app, "fetch", "--quiet", bare, f"+refs/heads/*:refs/remotes/{name}/*")
		self.git(app, "branch", "--quiet", f"--set-upstream-to={name}/{branch}")
		for number in range(1, ahead + 1):
			self.commit_file(app, f"ahead_{number}.txt", f"{number}\n", message=f"ahead commit {number}")

	def switch_branch(self, app, branch, *, create=True) -> None:
		self.git(app, "switch", "--quiet", *(("-c",) if create else ()), branch)

	def detach(self, app) -> None:
		self.git(app, "switch", "--quiet", "--detach")

	def mark_in_progress(self, app, kind) -> None:
		"""Leave the state file git writes mid-operation: `MERGE_HEAD`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`
		(the HEAD sha) or the `rebase-merge` directory (`head-name`, `onto`)."""
		if kind not in IN_PROGRESS_KINDS:
			raise ValueError(f"unknown in-progress kind: {kind!r}")
		head = self.git(app, "rev-parse", "HEAD")
		path = self._git_path(app, kind)
		if kind == "rebase-merge":
			branch = self.git(app, "symbolic-ref", "HEAD")
			os.makedirs(path, exist_ok=True)
			self._write_file(os.path.join(path, "head-name"), branch)
			self._write_file(os.path.join(path, "onto"), head)
		else:
			self._write_file(path, head)

	def hold_index_lock(self, app) -> None:
		"""Create `index.lock` as a concurrent git process would; later index writes fail."""
		self._write_file(self._git_path(app, "index.lock"), "")

	def install_marker_hooks(self, app) -> str:
		"""Install `MARKER_HOOKS` in the repo's hooks dir; return the marker dir (under `base`).

		Each hook touches `<markers>/<hook>`; `pre-commit` then refuses the commit. Helper commands never
		run them (`git(..., run_hooks=False)`); a test passes `run_hooks=True` to run them. A repo and its
		worktrees share one hooks dir, so a second install on it is refused.
		"""
		common = self.git(app, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
		hooks_dir = os.path.join(common, "hooks")
		if any(os.path.exists(os.path.join(hooks_dir, hook)) for hook in MARKER_HOOKS):
			raise ValueError(f"GitSandbox marker hooks already installed in {hooks_dir}")
		markers = os.path.join(self.base, "markers", app)
		os.makedirs(markers)
		os.makedirs(hooks_dir, exist_ok=True)
		for hook in MARKER_HOOKS:
			script = f'#!/bin/sh\ncat > /dev/null\ntouch "{markers}/{hook}"\n'
			if hook == "pre-commit":
				script += "exit 1\n"
			path = os.path.join(hooks_dir, hook)
			self._write_file(path, script)
			os.chmod(path, 0o755)
		return markers


ERP_AI_REPO = "erp_ai"
ERP_AI_SESSION_PATHS = ("docs", ".team", ".claude")


def _read_git(repo: str, *args: str) -> str:
	"""Stdout of read-only `git -C <repo> --no-optional-locks <args>`; inherited `GIT_*` dropped, no stdin."""
	env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
	env["LC_ALL"] = "C"
	command = ["git", "-C", repo, "--no-optional-locks", *args]
	completed = subprocess.run(
		command,
		env=env,
		stdin=subprocess.DEVNULL,
		capture_output=True,
		text=True,
		timeout=GIT_SANDBOX_TIMEOUT_S,
	)
	if completed.returncode != 0:
		raise AssertionError(f"{' '.join(command)} failed: {completed.stderr}")
	return completed.stdout


def erp_ai_code_state(repo: str) -> tuple[str, str]:
	"""`(top-level tree of HEAD, status --porcelain)` of `repo`, both without `ERP_AI_SESSION_PATHS` (NFR-14).

	Other sessions write and commit docs and team state under those names in the main checkout, so only the
	code part of the real `erp_ai` repo is compared (CHG-002 design R-11, addendum-4 P-2).
	"""
	tree = "".join(
		line
		for line in _read_git(repo, "ls-tree", "HEAD").splitlines(keepends=True)
		if line.rstrip("\n").split("\t", 1)[-1] not in ERP_AI_SESSION_PATHS
	)
	excludes = [f":(exclude){name}" for name in ERP_AI_SESSION_PATHS]
	return tree, _read_git(repo, "status", "--porcelain", "--", ".", *excludes)


def real_core_repos_snapshot() -> dict:
	"""`{app: (HEAD sha, status --porcelain)}` of the real core repos, plus `erp_ai: erp_ai_code_state(...)` (NFR-14).

	Read-only git, no optional locks.
	"""
	apps_dir = os.path.join(get_bench_path(), "apps")
	snapshot = {}
	for app in CORE_APPS:
		repo = os.path.join(apps_dir, app)
		head = _read_git(repo, "rev-parse", "HEAD")
		snapshot[app] = (head.strip(), _read_git(repo, "status", "--porcelain"))
	snapshot[ERP_AI_REPO] = erp_ai_code_state(os.path.join(apps_dir, ERP_AI_REPO))
	return snapshot


class RealCoreReposUntouchedMixin:
	"""Fail the test class when HEAD or `status --porcelain` of a real core repo changed while it ran (NFR-9, NFR-14).

	erp_ai: the code part only, without `ERP_AI_SESSION_PATHS` (`erp_ai_code_state`).
	"""

	@classmethod
	def setUpClass(cls):
		cls._real_core_repos_before = real_core_repos_snapshot()
		super().setUpClass()

	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		after = real_core_repos_snapshot()
		changed = [
			f"{app}: {cls._real_core_repos_before[app]!r} -> {after.get(app)!r}"
			for app in cls._real_core_repos_before
			if after.get(app) != cls._real_core_repos_before[app]
		]
		if changed:
			raise AssertionError("real core repos changed: " + "; ".join(changed))


SAMPLE_PROPOSAL_APP = "myapp"
SAMPLE_PROPOSAL_FILE = "myapp/myapp/ok.py"
SAMPLE_CONTENT_BEFORE = "x = 1\n"
SAMPLE_CONTENT_AFTER = "x = 2\n"


def _sha256_text(text: str) -> str:
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sample_code_fields() -> dict:
	diff = "".join(
		difflib.unified_diff(
			SAMPLE_CONTENT_BEFORE.splitlines(keepends=True),
			SAMPLE_CONTENT_AFTER.splitlines(keepends=True),
			fromfile=f"a/{SAMPLE_PROPOSAL_FILE}",
			tofile=f"b/{SAMPLE_PROPOSAL_FILE}",
		)
	)
	return {
		"change_kind": CHANGE_KIND_CODE,
		"app": SAMPLE_PROPOSAL_APP,
		"file_path": SAMPLE_PROPOSAL_FILE,
		"is_new_file": 0,
		"command_args": "",
		"base_hash": _sha256_text(SAMPLE_CONTENT_BEFORE),
		"content_before": SAMPLE_CONTENT_BEFORE,
		"content_after": SAMPLE_CONTENT_AFTER,
		"after_hash": _sha256_text(SAMPLE_CONTENT_AFTER),
		"diff": diff,
		"reversible": 1,
		"target_branch": "main",
		"upstream_ref": "origin/main",
		"ahead_count": 0,
		"is_core_app": 0,
		"commit_message": f"erp_ai: áp dụng đề xuất mẫu ({SAMPLE_PROPOSAL_FILE})\n\nNgười duyệt: <người duyệt>",
	}


def _sample_command_fields() -> dict:
	return {
		"change_kind": CHANGE_KIND_COMMAND,
		"app": SAMPLE_PROPOSAL_APP,
		"file_path": "",
		"is_new_file": 0,
		"command_args": json.dumps(["build", "--app", SAMPLE_PROPOSAL_APP]),
		"reversible": 0,
		"target_branch": "",
		"upstream_ref": "",
		"ahead_count": 0,
		"is_core_app": 0,
		"commit_message": "",
	}


def make_change_proposal(kind: str = CHANGE_KIND_CODE, ticket: str | None = None, **fields):
	"""Insert a `Chờ duyệt` ERP AI Change Proposal (file change with git fields, or bench command) and return it.

	`ticket` defaults to a new HD Ticket; `fields` override any sample value. Inserted with
	`ignore_permissions=True` and never committed: the caller's test rolls it back.
	"""
	if kind == CHANGE_KIND_CODE:
		values = _sample_code_fields()
	elif kind == CHANGE_KIND_COMMAND:
		values = _sample_command_fields()
	else:
		raise ValueError(f"unknown change kind: {kind!r}")
	if ticket is None:
		ticket = make_ticket(subject=_unique("change proposal")).name
	values.update(
		{
			"doctype": PROPOSAL_DOCTYPE,
			"ticket": ticket,
			"run_id": f"{PREFIX}run",
			"instructor": "Administrator",
			"reason": "Đề xuất mẫu cho test",
			"change_status": CHANGE_STATUS_PENDING,
		}
	)
	values.update(fields)
	return frappe.get_doc(values).insert(ignore_permissions=True)


def _block_operation(operation) -> FileOp:
	"""A `FileOp` from a `FileOp` or a dict of its field names; a missing hash is computed from the text."""
	if isinstance(operation, dict):
		operation = FileOp(
			**{
				"new_path": None,
				"before": None,
				"after": None,
				"base_hash": None,
				"after_hash": None,
				**operation,
			}
		)
	base_hash = operation.base_hash
	if base_hash is None and operation.before is not None:
		base_hash = _sha256_text(operation.before)
	after_hash = operation.after_hash
	if after_hash is None and operation.after is not None:
		after_hash = _sha256_text(operation.after)
	return FileOp(
		operation.kind,
		operation.path,
		operation.new_path,
		operation.before,
		operation.after,
		base_hash,
		after_hash,
	)


def _block_diff(operation: FileOp) -> str:
	"""Design 2.2 `diff` of one item: deletion against `/dev/null`, rename as `rename from` / `rename to`."""
	if operation.kind == CHANGE_OP_RENAME:
		return f"rename from {operation.path}\nrename to {operation.new_path}\n"
	before = "" if operation.before is None else operation.before
	after = "" if operation.after is None else operation.after
	return "".join(
		difflib.unified_diff(
			before.splitlines(keepends=True),
			after.splitlines(keepends=True),
			fromfile="/dev/null" if operation.kind == CHANGE_OP_CREATE else f"a/{operation.path}",
			tofile="/dev/null" if operation.kind == CHANGE_OP_DELETE else f"b/{operation.path}",
		)
	)


def _command_app(commands: list) -> str:
	"""Design 2.2: the app of a block with only commands is the one of its `build --app`, if any."""
	for args in commands:
		if args[:2] == ["build", "--app"] and len(args) > 2:
			return args[2]
	return ""


def make_block_proposal(operations, commands, ticket: str | None = None, **fields):
	"""Insert a `Chờ duyệt` ERP AI Change Proposal of the block shape (CHG-002 design 2.1, 2.2) and return it.

	`operations` is a list of `change_guard.FileOp` or dicts of its field names, stored as child rows in that
	order; a hash left `None` is computed from the text. `commands` is the argv list stored as `command_list`
	JSON. `ticket` defaults to a new HD Ticket; `fields` override any parent value. Inserted with
	`ignore_permissions=True` and never committed: the caller's test rolls it back.
	"""
	operations = [_block_operation(operation) for operation in operations]
	if ticket is None:
		ticket = make_ticket(subject=_unique("block proposal")).name
	values = {
		"doctype": PROPOSAL_DOCTYPE,
		"ticket": ticket,
		"run_id": f"{PREFIX}run",
		"instructor": "Administrator",
		"reason": "Đề xuất khối mẫu cho test",
		"change_status": CHANGE_STATUS_PENDING,
		"change_kind": CHANGE_KIND_CODE if operations else CHANGE_KIND_COMMAND,
		"app": operations[0].path.split("/", 1)[0] if operations else _command_app(commands),
		"reversible": 1 if operations else 0,
		"command_list": json.dumps(commands),
		"diff": "".join(_block_diff(operation) for operation in operations),
		"target_branch": "main" if operations else "",
		"upstream_ref": "origin/main" if operations else "",
		"ahead_count": 0,
		"is_core_app": 0,
		"operations": [
			{
				"doctype": OPERATION_DOCTYPE,
				"operation": operation.kind,
				"file_path": operation.path,
				"new_path": operation.new_path,
				"content_before": operation.before,
				"content_after": operation.after,
				"base_hash": operation.base_hash,
				"after_hash": operation.after_hash,
			}
			for operation in operations
		],
	}
	values.update(fields)
	return frappe.get_doc(values).insert(ignore_permissions=True)
