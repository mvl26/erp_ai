import hashlib
import re
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs

import frappe
import frappe.app
import frappe.handler
from frappe import _
from frappe.tests.utils import FrappeTestCase
from frappe.utils import background_jobs
from helpdesk.test_utils import create_agent, make_ticket, make_todo
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from erp_ai import change_decision
from erp_ai.agent import authority, change_link
from erp_ai.agent.changes import process_runner
from erp_ai.constants import (
	AGENT_USER,
	CHANGE_KIND_CODE,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_PENDING,
	CHANGE_STATUS_REJECTED,
	CHANGE_STATUS_STALE,
	LOG_DOCTYPE,
	PROPOSAL_DOCTYPE,
	ROLE_INSTRUCTOR,
	SETTING_DOCTYPE,
)
from erp_ai.test_utils import GitSandbox, make_change_proposal, set_agent_settings

INSTRUCTOR = "decision.instructor@example.com"
PLAIN = "decision.plain@example.com"
ASSIGNEE = "decision.assignee@example.com"
TICKET_CREATOR = "decision.creator@example.com"
DECIDE = "erp_ai.change_decision.decide"
RUN_CHANGE = "erp_ai.agent.changes.apply_job.run_change"
ROLE_REFUSAL = "Chỉ người có vai trò ERP AI Instructor mới duyệt, từ chối hoặc hoàn tác được"
BAD_LINK_REFUSAL = "Đường dẫn duyệt không hợp lệ hoặc đã bị sửa."
FORM_SCRIPT_PATH = (
	Path(__file__).resolve().parent
	/ "erp_ai_agent"
	/ "doctype"
	/ "erp_ai_change_proposal"
	/ "erp_ai_change_proposal.js"
)
# AC-27: a code proposal on a throw-away `GitSandbox` repo (never the real `apps/`).
SANDBOX_APP = "custom_app"
SANDBOX_REL = "pkg/mod.py"
CODE_BEFORE = "x = 1\n"
CODE_AFTER = "x = 2\n"
CODE_EDITED = "import os\n"


def _sha(text: str) -> str:
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _signature(name, action) -> str:
	"""The `_signature` the signed link of `change_link` carries for `name` + `action`."""
	return parse_qs(change_link._signed_query(name, action))["_signature"][0]


def _request(method: str) -> Request:
	return Request(EnvironBuilder(path=f"/api/method/{DECIDE}", method=method).get_environ())


def _not_whitelisted_for_guest() -> str:
	"""The exact text of `frappe.is_whitelisted` for a method Guest may not call."""
	summary = _("You are not permitted to access this resource. Login to access")
	detail = _("Function {0} is not whitelisted.").format(frappe.bold(DECIDE))
	return f"<details><summary>{summary}</summary>{detail}</details>"


class TestChangeDecision(FrappeTestCase):
	"""ADR-023 QĐ 1 / M1: the signed link opens the form, the form POSTs `decide` once (AC-5, AC-25, AC-26)."""

	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		# STD-TEST-6: the role edits of this class leave no cached role the site itself does not grant.
		for user in (AGENT_USER, INSTRUCTOR):
			cached = frappe.cache.hget("roles", user)
			granted = bool(frappe.db.exists("Has Role", {"parent": user, "role": ROLE_INSTRUCTOR}))
			if cached is not None and (ROLE_INSTRUCTOR in cached) != granted:
				raise AssertionError(f"stale roles cache for {user}: {cached}, site grants role: {granted}")

	def setUp(self):
		# `add_roles` re-caches the Redis `roles` hash; cleanups run in reverse, so these clear it after the rollback.
		for user in (AGENT_USER, INSTRUCTOR):
			self.addCleanup(frappe.clear_cache, user=user)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		for email in (INSTRUCTOR, PLAIN, ASSIGNEE, TICKET_CREATOR):
			create_agent(email)
		if not frappe.db.exists("User", AGENT_USER):
			create_agent(AGENT_USER)
		frappe.get_doc("User", INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		# The real `frappe.enqueue` runs; only the Redis queue behind it is a stub (no Redis in the test).
		self.queue = MagicMock(name="queue")
		for target, value in (("get_queue", self.queue), ("get_job", None)):
			stub = patch.object(background_jobs, target, return_value=value)
			stub.start()
			self.addCleanup(stub.stop)
		ticket = make_ticket(subject="decision ticket", raised_by=TICKET_CREATOR)
		self.proposal = make_change_proposal(ticket=ticket.name)

	def call(self, user, http_method, action, signature=None, name=None):
		"""Run `decide` the way a request does: `frappe.handler.execute_cmd` under `user` and `http_method`."""
		name = self.proposal.name if name is None else name
		form = frappe._dict(
			cmd=DECIDE,
			name=name,
			action=action,
			_signature=_signature(name, action) if signature is None else signature,
		)
		frappe.set_user(user)
		try:
			with (
				patch.object(frappe.local, "request", _request(http_method), create=True),
				patch.object(frappe.local, "form_dict", form),
			):
				return frappe.handler.execute_cmd(DECIDE)
		finally:
			frappe.set_user("Administrator")

	def end_request(self, http_method):
		"""`frappe.app.sync_database` at the end of the request; the SQL COMMIT itself is held back.

		Everything Frappe does around the commit runs (its `after_commit` callbacks queue the jobs);
		only the statements that would end the test transaction are swallowed.
		"""
		real_sql = frappe.db.sql
		self.sql_commits = 0

		def sql(query, *args, **kwargs):
			text = str(query).strip().lower()
			if text == "commit":
				self.sql_commits += 1
				return ()
			if text.startswith("start transaction"):
				return ()
			return real_sql(query, *args, **kwargs)

		with (
			patch.object(frappe.local, "request", _request(http_method), create=True),
			patch.object(frappe.db, "sql", side_effect=sql),
		):
			frappe.app.sync_database(rollback=False)

	def post(self, user, action, signature=None, name=None):
		result = self.call(user, "POST", action, signature=signature, name=name)
		self.end_request("POST")
		return result

	def status(self):
		return frappe.db.get_value(PROPOSAL_DOCTYPE, self.proposal.name, "change_status")

	def log_rows(self):
		return frappe.db.count(LOG_DOCTYPE, {"change_proposal": self.proposal.name})

	def jobs(self):
		return [
			call
			for call in self.queue.enqueue_call.call_args_list
			if call.kwargs["kwargs"]["method"] == RUN_CHANGE
		]

	def assertRefused(self, user, http_method, action, message, signature=None, name=None):
		"""Exactly `PermissionError(message)`; status, log rows and change jobs unchanged."""
		before = (self.status(), self.log_rows())
		with self.assertRaises(frappe.PermissionError) as caught:
			self.call(user, http_method, action, signature=signature, name=name)
		self.assertIs(type(caught.exception), frappe.PermissionError)
		self.assertEqual(str(caught.exception), message)
		frappe.clear_messages()
		self.assertEqual((self.status(), self.log_rows()), before)
		self.assertEqual(self.status(), CHANGE_STATUS_PENDING)
		self.assertEqual(self.jobs(), [])

	def test_method_is_post_only_and_never_guest(self):
		fn = change_decision.decide
		self.assertIn(fn, frappe.whitelisted)
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[fn], ["POST"])
		self.assertNotIn(fn, frappe.guest_methods)

	def test_get_is_refused_and_changes_nothing(self):
		for action in change_link.ACTIONS:
			with self.subTest(action=action):
				self.assertRefused(INSTRUCTOR, "GET", action, _("Not permitted"))

	def test_post_bad_signature_changed_action_or_name_writes_nothing(self):
		other = make_change_proposal()
		cases = {
			"wrong": ("approve", "0" * 128, None),
			"empty": ("approve", "", None),
			"action changed reject → approve": ("approve", _signature(self.proposal.name, "reject"), None),
			"name changed": ("approve", _signature(other.name, "approve"), None),
			"signed for the other name, sent for this one": (
				"approve",
				_signature(self.proposal.name, "approve"),
				other.name,
			),
			"unknown action": ("undo", "0" * 128, None),
		}
		for case, (action, signature, name) in cases.items():
			with self.subTest(case=case):
				self.assertRefused(
					INSTRUCTOR, "POST", action, BAD_LINK_REFUSAL, signature=signature, name=name
				)
				self.assertEqual(
					frappe.db.get_value(PROPOSAL_DOCTYPE, other.name, "change_status"), CHANGE_STATUS_PENDING
				)

	def test_post_approve_sets_approved_and_one_job_survives_request_end(self):
		result = self.call(INSTRUCTOR, "POST", "approve")

		self.assertEqual(result, {"ok": True, "status": CHANGE_STATUS_APPROVED})
		self.assertEqual(self.status(), CHANGE_STATUS_APPROVED)
		self.assertEqual(frappe.db.get_value(PROPOSAL_DOCTYPE, self.proposal.name, "decided_by"), INSTRUCTOR)
		# Queued after commit: nothing reaches the queue before the request ends.
		self.assertEqual(self.jobs(), [])

		self.end_request("POST")

		self.assertEqual(self.sql_commits, 1)
		(job,) = self.jobs()
		job_kwargs = job.kwargs["kwargs"]
		self.assertEqual(job_kwargs["user"], INSTRUCTOR)
		self.assertEqual(
			(job_kwargs["kwargs"]["proposal_name"], job_kwargs["kwargs"]["action"]),
			(self.proposal.name, "apply"),
		)

	def test_post_reject_zero_jobs(self):
		result = self.post(INSTRUCTOR, "reject")

		self.assertEqual(result, {"ok": True, "status": CHANGE_STATUS_REJECTED})
		self.assertEqual(self.status(), CHANGE_STATUS_REJECTED)
		self.assertEqual(self.jobs(), [])

	def test_replay_keeps_state_and_enqueues_nothing(self):
		self.post(INSTRUCTOR, "approve")
		self.assertEqual(len(self.jobs()), 1)
		rows = self.log_rows()

		for action, verb in (("approve", "duyệt"), ("reject", "từ chối")):
			with self.subTest(action=action):
				with self.assertRaises(frappe.ValidationError) as caught:
					self.post(INSTRUCTOR, action)
				frappe.clear_messages()
				self.assertEqual(
					str(caught.exception),
					f"Đề xuất đang ở trạng thái {CHANGE_STATUS_APPROVED}, không {verb} được",
				)
				self.assertEqual(self.status(), CHANGE_STATUS_APPROVED)
				self.assertEqual(self.log_rows(), rows)
				self.assertEqual(len(self.jobs()), 1)

	def test_refused_accounts(self):
		self.assertEqual(authority.NEVER_AUTHORITY, frozenset({"Administrator", "Guest", AGENT_USER}))
		# The agent account and Administrator hold the role, so only `NEVER_AUTHORITY` refuses them.
		frappe.get_doc("User", AGENT_USER).add_roles(ROLE_INSTRUCTOR)
		self.assertIn(ROLE_INSTRUCTOR, frappe.get_roles(AGENT_USER))
		self.assertIn(ROLE_INSTRUCTOR, frappe.get_roles("Administrator"))
		todo = make_todo(self.proposal.ticket, ASSIGNEE)
		frappe.db.set_value("ToDo", todo, "assigned_by", INSTRUCTOR)
		# The assignee's comments are instructions to the bot, yet the role is still missing.
		self.assertTrue(authority.is_instruction(ASSIGNEE, self.proposal.ticket))
		self.assertEqual(frappe.db.get_value("HD Ticket", self.proposal.ticket, "raised_by"), TICKET_CREATOR)
		accounts = {
			"agent account": (AGENT_USER, ROLE_REFUSAL),
			"Administrator": ("Administrator", ROLE_REFUSAL),
			"Guest": ("Guest", _not_whitelisted_for_guest()),
			"user without the role": (PLAIN, ROLE_REFUSAL),
			"assignee of the ticket": (ASSIGNEE, ROLE_REFUSAL),
			"creator of the ticket": (TICKET_CREATOR, ROLE_REFUSAL),
		}
		for account, (user, message) in accounts.items():
			for action in change_link.ACTIONS:
				with self.subTest(account=account, action=action):
					self.assertRefused(user, "POST", action, message)
		for user in (PLAIN, ASSIGNEE, TICKET_CREATOR):
			self.assertNotIn(ROLE_INSTRUCTOR, frappe.get_roles(user))

	def test_form_script_posts_once_without_confirm_and_strips_params(self):
		source = FORM_SCRIPT_PATH.read_text(encoding="utf-8")
		self.assertEqual(source.count(f'"{DECIDE}"'), 1)
		match = re.search(r"\nfunction decide_from_link\(frm\) \{\n(.*?)\n\}\n", source, re.DOTALL)
		self.assertIsNotNone(match, "decide_from_link(frm) missing")
		body = match.group(1)
		self.assertRegex(source, r"refresh\(frm\) \{\n\t\tdecide_from_link\(frm\);\n")
		for step in ('"action"', '"_signature"', 'frm.doc.change_status === "Chờ duyệt"', f'"{DECIDE}"'):
			self.assertIn(step, body)
		self.assertNotIn("frappe.confirm", body)
		self.assertNotIn("add_custom_button", body)
		self.assertEqual(body.count("frappe.call("), 1)
		self.assertIn("args: { name: frm.doc.name, action, _signature: signature },", body)
		self.assertIn('type: "POST",', body)
		self.assertEqual(body.count("history.replaceState("), 1)
		# The address is cleaned for every status, and before the call: a refresh cannot call twice.
		self.assertLess(
			body.index("history.replaceState("), body.index('frm.doc.change_status === "Chờ duyệt"')
		)
		self.assertLess(body.index("history.replaceState("), body.index("frappe.call("))
		self.assertLess(body.index("frappe.call("), body.index("frm.reload_doc()"))

	def sandbox_proposal(self) -> str:
		"""A `Chờ duyệt` code proposal on `SANDBOX_APP` of the sandbox that the job would apply as it stands."""
		return make_change_proposal(
			CHANGE_KIND_CODE,
			ticket=self.proposal.ticket,
			app=SANDBOX_APP,
			file_path=f"{SANDBOX_APP}/{SANDBOX_REL}",
			content_before=CODE_BEFORE,
			content_after=CODE_AFTER,
			base_hash=_sha(CODE_BEFORE),
			after_hash=_sha(CODE_AFTER),
			target_branch="main",
			upstream_ref="",
		).name

	def run_queued_job(self, name) -> dict:
		"""Run the one `apply` job `decide` queued for `name` as the worker does: under the job's `user`.

		The job's own `frappe.db.commit` is held back; returns the spies on every git write and bench run.
		"""
		(job,) = (call for call in self.jobs() if call.kwargs["kwargs"]["kwargs"]["proposal_name"] == name)
		job_kwargs = job.kwargs["kwargs"]
		self.assertEqual((job_kwargs["user"], job_kwargs["kwargs"]["action"]), (INSTRUCTOR, "apply"))
		patchers = {
			target: patch.object(process_runner, target, wraps=getattr(process_runner, target))
			for target in ("git_add_new", "git_commit_only", "run_bench")
		}
		frappe.set_user(job_kwargs["user"])
		try:
			with patch.object(frappe.db, "commit"):
				spies = {target: patcher.start() for target, patcher in patchers.items()}
				try:
					frappe.get_attr(job_kwargs["method"])(**job_kwargs["kwargs"])
				finally:
					for patcher in patchers.values():
						patcher.stop()
		finally:
			frappe.set_user("Administrator")
		return spies

	def sandbox_git(self, *args) -> str:
		return self.sandbox.git(SANDBOX_APP, *args).strip()

	def target_bytes(self) -> bytes:
		return (Path(self.sandbox.repo(SANDBOX_APP)) / SANDBOX_REL).read_bytes()

	def status_and_reason(self, name):
		return frappe.db.get_value(PROPOSAL_DOCTYPE, name, ["change_status", "failure_reason"])

	def change_rows(self, name):
		return frappe.get_all(
			LOG_DOCTYPE,
			filters={"change_proposal": name},
			fields=["change_step", "actor", "error", "ticket", "creation"],
			order_by="creation asc",
		)

	def clear_settings_cache_after_rollback(self):
		frappe.db.rollback()
		frappe.clear_document_cache(SETTING_DOCTYPE, SETTING_DOCTYPE)

	def test_link_approval_still_rechecked_at_apply(self):
		"""AC-27: each apply-time check still refuses after `decide`; 0 bytes, 0 commits, 0 runs, one log row."""
		# Runs before the class's rollback, so the switch and app list of this test leave no cached value.
		self.addCleanup(self.clear_settings_cache_after_rollback)
		self.sandbox = GitSandbox(self, apps=(SANDBOX_APP,), erp_ai_worktree=None)
		start = self.sandbox.commit_file(SANDBOX_APP, SANDBOX_REL, CODE_BEFORE)

		def reset():
			self.sandbox_git("checkout", "--quiet", "--force", "-B", "main", start)
			set_agent_settings(code_change_enabled=1, code_change_apps=SANDBOX_APP)

		def switch_off(name):
			set_agent_settings(code_change_enabled=0)

		def target_changed(name):
			self.sandbox.commit_file(SANDBOX_APP, SANDBOX_REL, "x = 99\n")

		def content_edited(name):
			# `after_hash` follows the edit, so only the digest taken at approval can tell.
			frappe.db.set_value(
				PROPOSAL_DOCTYPE,
				name,
				{"content_after": CODE_EDITED, "after_hash": _sha(CODE_EDITED)},
				update_modified=False,
			)

		def branch_changed(name):
			self.sandbox.switch_branch(SANDBOX_APP, "other")

		def app_removed(name):
			set_agent_settings(code_change_apps="other_app")

		# Control: with nothing changed after the link approval, the same fixture is applied.
		reset()
		name = self.sandbox_proposal()
		self.assertEqual(self.post(INSTRUCTOR, "approve", name=name)["status"], CHANGE_STATUS_APPROVED)
		self.run_queued_job(name)
		self.assertEqual(self.status_and_reason(name), (CHANGE_STATUS_APPLIED, None))
		self.assertEqual(self.target_bytes(), CODE_AFTER.encode("utf-8"))
		self.assertEqual(self.sandbox_git("rev-list", "--count", "HEAD"), "3")

		# Statuses and reasons of design 4.3 steps 4.2 and 4.3, written out by hand.
		cases = {
			"code switch off": (switch_off, CHANGE_STATUS_FAILED, "fail", "công tắc đang tắt"),
			"target file changed": (
				target_changed,
				CHANGE_STATUS_STALE,
				"stale",
				"file đích đã đổi kể từ lúc đề xuất",
			),
			"content no longer matches the approved digest": (
				content_edited,
				CHANGE_STATUS_FAILED,
				"fail",
				"nội dung đề xuất đã bị sửa sau khi duyệt",
			),
			"checked-out branch changed": (
				branch_changed,
				CHANGE_STATUS_STALE,
				"stale",
				"nhánh đang checkout đã đổi kể từ lúc đề xuất",
			),
			"app removed from the allowed list": (
				app_removed,
				CHANGE_STATUS_FAILED,
				"fail",
				"mục 1 (custom_app/pkg/mod.py): app không có trong danh sách được sửa",
			),
		}
		for case, (change, status, step, reason) in cases.items():
			with self.subTest(case=case):
				reset()
				name = self.sandbox_proposal()
				self.assertEqual(
					self.post(INSTRUCTOR, "approve", name=name)["status"], CHANGE_STATUS_APPROVED
				)
				change(name)
				before = (self.target_bytes(), self.sandbox_git("rev-parse", "HEAD"))
				count = self.sandbox_git("rev-list", "--count", "HEAD")
				worktree = self.sandbox_git("status", "--porcelain")

				spies = self.run_queued_job(name)

				self.assertEqual(self.status_and_reason(name), (status, reason))
				self.assertEqual((self.target_bytes(), self.sandbox_git("rev-parse", "HEAD")), before)
				self.assertEqual(self.sandbox_git("rev-list", "--count", "HEAD"), count)
				self.assertEqual(self.sandbox_git("status", "--porcelain"), worktree)
				self.assertEqual(
					{target: spy.call_count for target, spy in spies.items()}, dict.fromkeys(spies, 0)
				)
				self.assertEqual(
					[(row.change_step, row.actor, row.error) for row in self.change_rows(name)],
					[("approve", INSTRUCTOR, None), (step, INSTRUCTOR, reason)],
				)

	def test_decide_logs_exactly_one_row_with_the_caller_as_actor(self):
		"""AC-12: one `decide` call, one log row, naming the user who called it."""
		for action, status in (("approve", CHANGE_STATUS_APPROVED), ("reject", CHANGE_STATUS_REJECTED)):
			with self.subTest(action=action):
				# Proposed for someone else than the caller: the row names the caller only by being right.
				name = make_change_proposal(ticket=self.proposal.ticket, instructor=TICKET_CREATOR).name
				self.assertEqual(self.change_rows(name), [])

				self.assertEqual(self.post(INSTRUCTOR, action, name=name)["status"], status)

				(row,) = self.change_rows(name)
				self.assertEqual(
					(row.change_step, row.actor, row.error, row.ticket),
					(action, INSTRUCTOR, None, self.proposal.ticket),
				)
				self.assertIsNotNone(row.creation)
				self.assertEqual(frappe.db.get_value(PROPOSAL_DOCTYPE, name, "decided_by"), INSTRUCTOR)
