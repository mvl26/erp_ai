import json
import os
import tempfile
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import policy
from erp_ai.eval import export_tickets
from erp_ai.test_utils import set_agent_settings

PREFIX = "ERPAI-TEST-"
EXCLUDED = "ERPAI-TEST-Excluded Team"
OPEN_TEAM = "ERPAI-TEST-Open Team"
KEYS = {"subject", "description", "ticket_type", "agent_group", "priority", "owner"}


def _ensure_team(name):
	if frappe.db.exists("HD Team", name):
		return
	frappe.get_doc({"doctype": "HD Team", "team_name": name, "users": [{"user": "Administrator"}]}).insert(
		ignore_permissions=True
	)


class TestExportTickets(FrappeTestCase):
	def setUp(self):
		# Never delete_doc HD Team (on_trash commits); drop the stale Redis rule map after rollback.
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		log_guard = patch.object(frappe, "log_error")
		log_guard.start()
		self.addCleanup(log_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")

		tmp = tempfile.TemporaryDirectory()
		self.addCleanup(tmp.cleanup)
		self.tmp = os.path.realpath(tmp.name)

		set_agent_settings(enabled=0, excluded_teams=EXCLUDED)
		for team in (EXCLUDED, OPEN_TEAM):
			_ensure_team(team)
		self.ticket_type = frappe.get_all("HD Ticket Type", pluck="name", limit=1)[0]
		self.priority = frappe.get_all("HD Ticket Priority", pluck="name", limit=1)[0]

	def _ticket(self, label, team=OPEN_TEAM, **extra):
		ticket = make_ticket(subject=f"{PREFIX}{label}", description=f"desc {label}")
		values = {"ticket_type": self.ticket_type, "agent_group": team, "priority": self.priority, **extra}
		for key, value in values.items():
			frappe.db.set_value("HD Ticket", ticket.name, key, value)
		return ticket.name

	def _rows(self, path):
		with open(path, encoding="utf-8") as handle:
			rows = [json.loads(line) for line in handle if line.strip()]
		return [row for row in rows if row["subject"].startswith(PREFIX)]

	def _path(self):
		return os.path.join(self.tmp, "tickets.jsonl")

	def test_export_skips_excluded_team(self):
		self._ticket("one")
		self._ticket("two")
		self._ticket("hr", team=EXCLUDED)
		path = self._path()

		written = export_tickets.export(path)

		rows = self._rows(path)
		self.assertEqual(sorted(row["subject"] for row in rows), [PREFIX + "one", PREFIX + "two"])
		self.assertGreaterEqual(written, 2)
		for row in rows:
			self.assertEqual(set(row), KEYS)
			self.assertEqual(row["agent_group"], OPEN_TEAM)
			self.assertEqual(row["ticket_type"], self.ticket_type)
			self.assertEqual(row["priority"], self.priority)
			self.assertEqual(row["owner"], "Administrator")

	def test_export_returns_number_of_lines_written(self):
		self._ticket("count")
		path = self._path()

		written = export_tickets.export(path)

		with open(path, encoding="utf-8") as handle:
			self.assertEqual(written, len(handle.readlines()))

	def test_export_skips_opt_out_and_runs_when_disabled(self):
		self._ticket("keep")
		self._ticket("optout", ai_opt_out=1)
		set_agent_settings(enabled=0)
		path = self._path()

		export_tickets.export(path)

		self.assertEqual([row["subject"] for row in self._rows(path)], [PREFIX + "keep"])

	def test_export_skips_tickets_without_ticket_type(self):
		self._ticket("labeled")
		self._ticket("notype", ticket_type="")
		path = self._path()

		export_tickets.export(path)

		self.assertEqual([row["subject"] for row in self._rows(path)], [PREFIX + "labeled"])

	def test_export_keeps_labeled_ticket_with_empty_group_and_priority(self):
		self._ticket("partial", team="", priority="")
		path = self._path()

		export_tickets.export(path)

		self.assertEqual([row["subject"] for row in self._rows(path)], [PREFIX + "partial"])

	def test_export_queries_every_send_policy_field(self):
		self._ticket("fields")
		seen = []

		def spy(ticket):
			seen.append(set(policy.SEND_POLICY_FIELDS) - set(ticket))
			return True

		with patch.object(policy, "can_send_ticket", side_effect=spy):
			export_tickets.export(self._path())

		self.assertTrue(seen)
		self.assertEqual([missing for missing in seen if missing], [])

	def test_export_never_writes_attachment_content(self):
		name = self._ticket("attach")
		attachment = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "ERPAI-TEST-secret.txt",
				"attached_to_doctype": "HD Ticket",
				"attached_to_name": name,
				"is_private": 1,
				"content": "ERPAI-TEST-FILE-CONTENT",
			}
		)
		attachment.insert(ignore_permissions=True)
		# Rollback drops the record, not the physical file: remove exactly the file we created.
		physical = attachment.get_full_path()
		self.addCleanup(lambda: os.path.exists(physical) and os.remove(physical))
		path = self._path()

		export_tickets.export(path)

		with open(path, encoding="utf-8") as handle:
			text = handle.read()
		self.assertNotIn("ERPAI-TEST-FILE-CONTENT", text)
		self.assertNotIn("ERPAI-TEST-secret", text)

	def _repo_dir(self):
		return os.path.dirname(os.path.realpath(frappe.get_app_path("erp_ai")))

	def _assert_refused(self, path):
		with self.assertRaises(ValueError) as ctx:
			export_tickets.export(path)
		self.assertEqual(str(ctx.exception), "Không ghi dữ liệu phiếu vào repo")
		self.assertFalse(os.path.exists(os.path.realpath(path)))

	def test_export_refuses_path_inside_repo(self):
		self._assert_refused(os.path.join(self._repo_dir(), "ERPAI-TEST-out.jsonl"))

	def test_export_refuses_dotdot_path_into_repo(self):
		# Climb to the filesystem root, then walk back down into the repo.
		repo_relative = os.path.relpath(self._repo_dir(), "/")
		sneaky = os.path.join(self.tmp, *([".."] * 20), repo_relative, "ERPAI-TEST-dd.jsonl")
		self._assert_refused(sneaky)

	def test_export_refuses_symlink_into_repo(self):
		link = os.path.join(self.tmp, "link")
		os.symlink(self._repo_dir(), link)
		self._assert_refused(os.path.join(link, "ERPAI-TEST-sl.jsonl"))

	def test_export_allows_path_outside_repo(self):
		self._ticket("ok")
		path = self._path()

		export_tickets.export(path)

		self.assertTrue(os.path.exists(path))
