import hashlib
import json
import os
import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_bench_path

from erp_ai import test_utils
from erp_ai.agent.changes import block
from erp_ai.agent.tools.change_guard import FileOp
from erp_ai.constants import (
	AGENT_USER,
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_OP_CREATE,
	CHANGE_OP_DELETE,
	CHANGE_OP_EDIT,
	CHANGE_OP_RENAME,
	CHANGE_STATUS_PENDING,
	CORE_APPS,
	HELPDESK_AGENT_ROLE,
	PROPOSAL_DOCTYPE,
	ROLE_AGENT,
)
from erp_ai.test_utils import (
	PREFIX,
	GitSandbox,
	make_active_agent,
	make_block_proposal,
	make_routing_rules,
	make_sla,
	make_team,
	pin_agent_roles,
	real_core_repos_snapshot,
)

AUTOMATIC_ROLES = {"Guest", "All", "Administrator", "Desk User"}
STRAY_ROLE = "Blogger"
PINNED = (ROLE_AGENT, HELPDESK_AGENT_ROLE)


def _roles() -> set[str]:
	return set(frappe.get_all("Has Role", filters={"parent": AGENT_USER, "parenttype": "User"}, pluck="role"))


def _rows() -> list[tuple]:
	rows = frappe.get_all(
		"Has Role",
		filters={"parent": AGENT_USER, "parenttype": "User"},
		fields=["name", "role", "parentfield"],
		order_by="name",
	)
	return [(row.name, row.role, row.parentfield) for row in rows]


class TestPinAgentRoles(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		# Registered first so it is undone last: the rollback cleanup runs while commits are still guarded.
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)

	def test_pin_agent_roles_sets_exact_set_and_restores(self):
		if STRAY_ROLE not in _roles():
			frappe.get_doc(
				{
					"doctype": "Has Role",
					"parent": AGENT_USER,
					"parenttype": "User",
					"parentfield": "roles",
					"role": STRAY_ROLE,
				}
			).insert(ignore_permissions=True)
		before_rows = _rows()
		inner = unittest.TestCase()

		pin_agent_roles(inner)

		self.assertEqual(_roles() - AUTOMATIC_ROLES, {ROLE_AGENT, HELPDESK_AGENT_ROLE})
		self.assertIn(ROLE_AGENT, frappe.get_roles(AGENT_USER))
		self.assertNotIn(STRAY_ROLE, frappe.get_roles(AGENT_USER))

		inner.doCleanups()

		self.assertEqual(_rows(), before_rows)
		self.assertIn(STRAY_ROLE, _roles())

	def test_pin_agent_roles_restores_state_changed_after_pinning(self):
		before_rows = _rows()
		inner = unittest.TestCase()
		pin_agent_roles(inner)
		frappe.db.delete("Has Role", {"parent": AGENT_USER, "parenttype": "User", "role": ROLE_AGENT})

		inner.doCleanups()

		self.assertEqual(_rows(), before_rows)

	def _add_role(self, role):
		if role not in _roles():
			frappe.get_doc(
				{
					"doctype": "Has Role",
					"parent": AGENT_USER,
					"parenttype": "User",
					"parentfield": "roles",
					"role": role,
				}
			).insert(ignore_permissions=True)

	def test_pin_agent_roles_adds_missing_pinned_roles(self):
		cases = {
			"agent role missing": (ROLE_AGENT,),
			"helpdesk role missing": (HELPDESK_AGENT_ROLE,),
			"both missing": (ROLE_AGENT, HELPDESK_AGENT_ROLE),
		}
		for label, missing in cases.items():
			with self.subTest(label):
				for role in PINNED:
					self._add_role(role)
				frappe.db.delete(
					"Has Role", {"parent": AGENT_USER, "parenttype": "User", "role": ("in", list(missing))}
				)
				before_rows = _rows()
				self.assertFalse(set(missing) & _roles())
				inner = unittest.TestCase()

				pin_agent_roles(inner)

				self.assertEqual(_roles() - AUTOMATIC_ROLES, set(PINNED))
				self.assertLessEqual(set(PINNED), set(frappe.get_roles(AGENT_USER)))

				inner.doCleanups()

				self.assertEqual(_rows(), before_rows)
				self.assertFalse(set(missing) & _roles())

	def test_pin_agent_roles_keeps_automatic_roles(self):
		self._add_role("Desk User")
		before_rows = _rows()
		inner = unittest.TestCase()

		pin_agent_roles(inner)

		self.assertIn("Desk User", _roles())
		inner.doCleanups()

		self.assertEqual(_rows(), before_rows)
		self.assertIn("Desk User", _roles())

	def test_pin_agent_roles_clears_cache_even_when_restore_fails(self):
		inner = unittest.TestCase()
		with patch.object(frappe, "clear_cache") as clear_cache:
			pin_agent_roles(inner)
			clear_cache.reset_mock()
			with patch.object(frappe.db, "delete", side_effect=RuntimeError("restore failed")):
				self.assertFalse(inner.doCleanups())

		clear_cache.assert_called_once_with(user=AGENT_USER)


class TestMakeHelpers(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		# Registered first so it is undone last: the rollback cleanup runs while commits are still guarded.
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)

	def test_make_routing_rules_is_valid_shape_without_users(self):
		rules = json.loads(make_routing_rules())
		self.assertEqual(set(rules), {"assignees", "departments", "importance_priority", "expected_sla"})
		self.assertEqual(set(rules["assignees"]), {"A", "B", "C", "F"})
		self.assertEqual(rules["assignees"]["A"], {"default": "", "prefixes": {}})
		self.assertEqual(rules["importance_priority"], {"1": "", "2": "High", "3": "High"})
		self.assertEqual(set(rules["expected_sla"]), set("ABCDEF"))

	def test_make_routing_rules_overrides_replace_top_level_keys(self):
		departments = {"Kế toán": {"team": "T", "head": "u@example.com"}}
		rules = json.loads(make_routing_rules(departments=departments))
		self.assertEqual(rules["departments"], departments)
		self.assertEqual(set(rules["assignees"]), {"A", "B", "C", "F"})

	def test_make_active_agent_returns_active_hd_agent(self):
		user = make_active_agent(self)
		self.assertTrue(user)
		self.assertNotEqual(user, AGENT_USER)
		self.assertEqual(frappe.db.get_value("HD Agent", {"user": user}, "is_active"), 1)
		self.assertNotEqual(make_active_agent(self), user)

	def test_make_team_with_rule_has_enabled_rule(self):
		member = make_active_agent(self)
		team = make_team(self, with_rule=True, rule_users=(member,))
		self.assertTrue(frappe.db.exists("HD Team", team))
		self.assertTrue(team.startswith(PREFIX))
		rule = frappe.db.get_value("HD Team", team, "assignment_rule")
		self.assertTrue(rule)
		self.assertEqual(frappe.db.get_value("Assignment Rule", rule, "disabled"), 0)
		users = frappe.get_all("Assignment Rule User", filters={"parent": rule}, pluck="user")
		self.assertEqual(users, [member])

	def test_make_team_without_rule_has_no_assignment_rule(self):
		team = make_team(self)
		self.assertTrue(frappe.db.exists("HD Team", team))
		self.assertFalse(frappe.db.get_value("HD Team", team, "assignment_rule"))
		self.assertFalse(frappe.db.exists("Assignment Rule", {"name": ("like", f"{team}%")}))
		self.assertFalse(frappe.db.exists("Assignment Rule User", {"parent": ("like", f"{team}%")}))

	def test_make_sla_sets_condition_default_enabled(self):
		sla = make_sla(self, condition="doc.priority == 'High'", default=True, enabled=False)
		self.assertTrue(sla.startswith(PREFIX))
		values = frappe.db.get_value(
			"HD Service Level Agreement", sla, ["condition", "default_sla", "enabled"], as_dict=True
		)
		self.assertEqual(values.condition, "doc.priority == 'High'")
		self.assertEqual(values.default_sla, 1)
		self.assertEqual(values.enabled, 0)
		plain = make_sla(self)
		self.assertEqual(
			frappe.db.get_value(
				"HD Service Level Agreement", plain, ["default_sla", "enabled"], as_dict=True
			),
			{"default_sla": 0, "enabled": 1},
		)
		priorities = frappe.get_all("HD Service Level Priority", filters={"parent": plain}, pluck="priority")
		self.assertEqual(set(priorities), {"Low", "Medium", "High", "Urgent"})


def _sha256(text: str) -> str:
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestMakeBlockProposal(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		# Registered first so it is undone last: the rollback cleanup runs while commits are still guarded.
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)

	def test_rows_hashes_and_command_list_stored(self):
		operations = [
			FileOp(CHANGE_OP_EDIT, "myapp/myapp/a.py", None, "a = 1\n", "a = 2\n", None, None),
			{"kind": CHANGE_OP_CREATE, "path": "myapp/myapp/new/b.py", "after": "b = 1\n"},
			FileOp(CHANGE_OP_DELETE, "myapp/myapp/c.py", None, "c = 1\n", None, None, None),
			{
				"kind": CHANGE_OP_RENAME,
				"path": "myapp/myapp/d.py",
				"new_path": "myapp/myapp/e.py",
				"before": "d = 1\n",
				"after": "d = 1\n",
			},
		]
		commands = [["build", "--app", "myapp"], ["restart"]]

		doc = make_block_proposal(operations, commands, reason="khối mẫu")

		stored = frappe.get_doc(PROPOSAL_DOCTYPE, doc.name)
		self.assertEqual(stored.change_status, CHANGE_STATUS_PENDING)
		self.assertEqual(stored.change_kind, CHANGE_KIND_CODE)
		self.assertEqual(stored.reason, "khối mẫu")
		self.assertEqual(stored.app, "myapp")
		self.assertEqual(stored.reversible, 1)
		self.assertTrue(stored.ticket)
		for fieldname in (
			"file_path",
			"content_before",
			"content_after",
			"base_hash",
			"after_hash",
			"command_args",
		):
			self.assertFalse(stored.get(fieldname), fieldname)
		self.assertEqual(json.loads(stored.command_list), commands)
		rows = [
			(
				row.idx,
				row.operation,
				row.file_path,
				row.new_path or None,
				row.base_hash or None,
				row.after_hash or None,
			)
			for row in sorted(stored.operations, key=lambda row: row.idx)
		]
		self.assertEqual(
			rows,
			[
				(1, CHANGE_OP_EDIT, "myapp/myapp/a.py", None, _sha256("a = 1\n"), _sha256("a = 2\n")),
				(2, CHANGE_OP_CREATE, "myapp/myapp/new/b.py", None, None, _sha256("b = 1\n")),
				(3, CHANGE_OP_DELETE, "myapp/myapp/c.py", None, _sha256("c = 1\n"), None),
				(
					4,
					CHANGE_OP_RENAME,
					"myapp/myapp/d.py",
					"myapp/myapp/e.py",
					_sha256("d = 1\n"),
					_sha256("d = 1\n"),
				),
			],
		)
		self.assertTrue(block.is_block(stored))
		self.assertEqual(block.commands_of(stored), commands)
		read_back = block.operations_of(stored)
		self.assertEqual([op.before for op in read_back], ["a = 1\n", None, "c = 1\n", "d = 1\n"])
		self.assertEqual([op.after for op in read_back], ["a = 2\n", "b = 1\n", None, "d = 1\n"])
		self.assertIn("myapp/myapp/a.py", stored.diff)
		self.assertIn("rename from myapp/myapp/d.py", stored.diff)

	def test_explicit_hash_kept_and_commands_only_block_is_bench_command(self):
		wrong = "0" * 64
		doc = make_block_proposal(
			[FileOp(CHANGE_OP_EDIT, "myapp/myapp/a.py", None, "a = 1\n", "a = 2\n", wrong, None)], []
		)
		self.assertEqual(doc.operations[0].base_hash, wrong)
		self.assertEqual(doc.operations[0].after_hash, _sha256("a = 2\n"))
		self.assertEqual(json.loads(doc.command_list), [])

		commands_only = make_block_proposal([], [["build", "--app", "hrms"]], ticket=doc.ticket)
		self.assertEqual(commands_only.change_kind, CHANGE_KIND_COMMAND)
		self.assertEqual(commands_only.app, "hrms")
		self.assertEqual(commands_only.reversible, 0)
		self.assertEqual(commands_only.ticket, doc.ticket)
		self.assertFalse(commands_only.operations)
		self.assertTrue(block.is_block(commands_only))


class TestRealCoreRepos(FrappeTestCase):
	def test_snapshot_includes_erp_ai(self):
		snapshot = real_core_repos_snapshot()

		self.assertEqual(set(snapshot), {*CORE_APPS, "erp_ai"})
		repo = os.path.join(get_bench_path(), "apps", "erp_ai")
		self.assertEqual(snapshot["erp_ai"], test_utils.erp_ai_code_state(repo))

	def test_erp_ai_code_state_ignores_session_paths_only(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		repo = sandbox.repo("custom_app")
		start = test_utils.erp_ai_code_state(repo)
		self.assertIn("\tREADME.md\n", start[0])
		self.assertEqual(start[1], "")

		sandbox.commit_file("custom_app", "docs/team/x.md", "a\n")
		sandbox.commit_file("custom_app", ".team/current.json", "{}\n")
		sandbox.commit_file("custom_app", ".claude/agent-memory/a.md", "a\n")
		sandbox.write_unstaged("custom_app", ".team/miyano-site.lock", "")
		sandbox.write_unstaged("custom_app", ".claude/m.md", "m\n")
		sandbox.write_unstaged("custom_app", "docs/team/x.md", "b\n")
		self.assertNotEqual(sandbox.git("custom_app", "status", "--porcelain"), "")
		self.assertEqual(test_utils.erp_ai_code_state(repo), start)

		sandbox.write_unstaged("custom_app", "README2.md", "x\n")
		untracked = test_utils.erp_ai_code_state(repo)
		self.assertEqual(untracked[0], start[0])
		self.assertEqual(untracked[1], "?? README2.md\n")

		sandbox.commit_file("custom_app", "pkg/x.py", "x = 1\n")
		committed = test_utils.erp_ai_code_state(repo)
		self.assertNotEqual(committed[0], start[0])
		self.assertIn("\tpkg\n", committed[0])
		self.assertEqual(test_utils.ERP_AI_SESSION_PATHS, ("docs", ".team", ".claude"))

	def test_erp_ai_code_state_fails_on_git_error(self):
		sandbox = GitSandbox(self, apps=(), erp_ai_worktree=None)
		with self.assertRaisesRegex(AssertionError, "ls-tree HEAD failed"):
			test_utils.erp_ai_code_state(sandbox.root)
