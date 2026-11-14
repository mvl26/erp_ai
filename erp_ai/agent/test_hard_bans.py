import ast
import inspect
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import hard_bans, policy
from erp_ai.agent.tools import read, site_api
from erp_ai.test_utils import keep_agent_settings

REASON_DENIED = "DocType bị cấm với bot (dữ liệu của app, tài khoản hoặc dữ liệu nhạy cảm)"
REASON_PERMISSION = "DocType phân quyền"
REASON_SUBMITTABLE = "chứng từ submit"
ALLOWED_IMPORTS = frozenset({"frappe", "erp_ai.agent.tools.read", "erp_ai.agent.tools.site_api"})
HARD_BANS_MODULE = "erp_ai.agent.hard_bans"


def _module_tree(module) -> ast.AST:
	return ast.parse(inspect.getsource(module))


def _imported_modules(tree: ast.AST) -> set:
	"""Module names a file imports; `from pkg import mod` counts as `pkg.mod` when that is an allowed module."""
	modules = set()
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			modules.update(alias.name for alias in node.names)
		elif isinstance(node, ast.ImportFrom):
			for alias in node.names:
				full = f"{node.module}.{alias.name}"
				modules.add(full if full in ALLOWED_IMPORTS or full == HARD_BANS_MODULE else node.module)
	return modules


class TestHardBanReason(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)

	def _submittable_outside_ban_sets(self) -> str:
		banned = read.denied_doctypes() | set(site_api.PERMISSION_DOCTYPES)
		names = frappe.get_all("DocType", {"is_submittable": 1, "istable": 0}, pluck="name", order_by="name")
		free = [name for name in names if name not in banned]
		self.assertTrue(free, "the site has no submittable DocType outside the ban sets")
		return free[0]

	def test_reasons_in_order(self):
		app_doctype = frappe.get_all("DocType", {"module": read.AI_MODULE}, pluck="name", limit=1)[0]
		self.assertEqual(hard_bans.hard_ban_reason(app_doctype), REASON_DENIED)
		self.assertIn(hard_bans.hard_ban_reason("Custom Role"), (REASON_PERMISSION, REASON_DENIED))
		self.assertEqual(hard_bans.hard_ban_reason(self._submittable_outside_ban_sets()), REASON_SUBMITTABLE)
		self.assertIsNone(hard_bans.hard_ban_reason("ToDo"))

	def test_permission_set_gives_permission_reason(self):
		only_in_site_api = set(site_api.PERMISSION_DOCTYPES) - read.denied_doctypes()
		self.assertTrue(only_in_site_api)
		for doctype in only_in_site_api:
			self.assertEqual(hard_bans.hard_ban_reason(doctype), REASON_PERMISSION, doctype)

	def test_permission_doctypes_banned(self):
		# INT-1 (F-3): every name of FEAT-004's permission set is banned; Role is only there, not in read's set.
		for doctype in site_api.PERMISSION_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertIn(hard_bans.hard_ban_reason(doctype), (REASON_PERMISSION, REASON_DENIED))
		self.assertNotIn("Role", read.denied_doctypes())
		self.assertEqual(hard_bans.hard_ban_reason("Role"), REASON_PERMISSION)
		# The set is read live: a DocType with no other ban gets the permission reason only while it is in the set.
		self.assertIsNone(hard_bans.hard_ban_reason("ToDo"))
		with patch.object(site_api, "PERMISSION_DOCTYPES", frozenset({"ToDo"})):
			self.assertEqual(hard_bans.hard_ban_reason("ToDo"), REASON_PERMISSION)
			self.assertIsNone(hard_bans.hard_ban_reason("Role"))

	def test_first_matching_reason_wins(self):
		submittable = self._submittable_outside_ban_sets()
		with patch.object(read, "denied_doctypes", return_value={submittable, "Custom Role"}):
			self.assertEqual(hard_bans.hard_ban_reason(submittable), REASON_DENIED)
			self.assertEqual(hard_bans.hard_ban_reason("Custom Role"), REASON_DENIED)
		with patch.object(site_api, "PERMISSION_DOCTYPES", frozenset({submittable})):
			self.assertEqual(hard_bans.hard_ban_reason(submittable), REASON_PERMISSION)

	def test_follows_denied_doctypes_source_live(self):
		fake = "ERPAI-TEST-not-a-doctype"
		with patch.object(read, "denied_doctypes", return_value={fake}):
			self.assertEqual(hard_bans.hard_ban_reason(fake), REASON_DENIED)

	def test_unknown_doctype_raises(self):
		with self.assertRaises(frappe.DoesNotExistError):
			hard_bans.hard_ban_reason("ERPAI-TEST-no-such-doctype")

	def test_no_doctype_literal_in_module(self):
		tree = _module_tree(hard_bans)
		doctype_names = set(frappe.get_all("DocType", pluck="name"))
		literals = {
			node.value
			for node in ast.walk(tree)
			if isinstance(node, ast.Constant) and isinstance(node.value, str)
		}
		self.assertEqual(literals & doctype_names, set())
		self.assertLessEqual(_imported_modules(tree), ALLOWED_IMPORTS)

	def test_policy_does_not_import_hard_bans(self):
		self.assertNotIn(HARD_BANS_MODULE, _imported_modules(_module_tree(policy)))
