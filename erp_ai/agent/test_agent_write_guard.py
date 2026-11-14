import json

import frappe
import frappe.client
from frappe.desk.form.save import savedocs
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.agent_write_guard import AGENT_WRITE_FLAG, allow_agent_write, refuse_agent_write
from erp_ai.constants import AGENT_USER, CREDENTIAL_DOCTYPE, SETTING_DOCTYPE
from erp_ai.test_utils import add_credential

GUARDED_HOOKS = ("before_insert", "validate", "on_trash", "before_rename", "before_submit", "before_cancel")
# As frappe.model.rename_doc passes them: old name, new name, merge.
HOOK_ARGUMENTS = {"before_rename": ("old-name", "new-name", False)}
REFUSAL = "Tài khoản agent không được ghi"
TEST_LABEL = "ERPAI-TEST-write-guard"
HUMAN_USER = "erpai-test-write-guard-sm@example.com"
SAVEPOINT = "erp_ai_write_guard_path"
# The DocType names spelled with a JSON escape, as a model could send them through call_method.
SETTING_ESCAPED = "ERP AI \\u0053etting"
CREDENTIAL_ESCAPED = "ERP AI \\u0043redential"


def _snapshot() -> tuple:
	"""The saved setting and every key row, as stored in the DB."""
	singles = frappe.db.sql(
		"select field, value from tabSingles where doctype=%s order by field", SETTING_DOCTYPE
	)
	rows = frappe.db.sql(
		"select * from `tabERP AI Credential` where parenttype=%s order by name",
		SETTING_DOCTYPE,
		as_dict=True,
	)
	return tuple(singles), tuple(tuple(sorted(row.items())) for row in rows)


def _credential_dict(**fields) -> dict:
	return {
		"doctype": CREDENTIAL_DOCTYPE,
		"parent": SETTING_DOCTYPE,
		"parenttype": SETTING_DOCTYPE,
		"parentfield": "credentials",
		"label": "ERPAI-TEST-forged",
		"api_key": "sk-forged",
		**fields,
	}


class TestAgentWriteGuard(FrappeTestCase):
	def setUp(self):
		# Cleanups run last-in first-out: user back, then rollback, then the agent's role cache.
		self.addCleanup(frappe.clear_cache, user=AGENT_USER)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(frappe.flags.pop, AGENT_WRITE_FLAG, None)
		frappe.set_user("Administrator")
		frappe.flags.pop(AGENT_WRITE_FLAG, None)
		if not frappe.db.exists("User", AGENT_USER):
			raise AssertionError(f"{AGENT_USER} does not exist on this site")
		# Worst case of ADR-023: the agent account is a System Manager, so Frappe's own permissions let it through.
		if "System Manager" not in frappe.get_roles(AGENT_USER):
			frappe.get_doc(
				{
					"doctype": "Has Role",
					"parent": AGENT_USER,
					"parenttype": "User",
					"parentfield": "roles",
					"role": "System Manager",
				}
			).db_insert()
			frappe.clear_cache(user=AGENT_USER)
		self.row = add_credential(TEST_LABEL)

	def _assert_refused(self, write):
		"""Run `write` as the agent: refused by the guard and the DB unchanged; undone so the next path starts clean."""
		before = _snapshot()
		frappe.db.savepoint(SAVEPOINT)
		frappe.set_user(AGENT_USER)
		try:
			with self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
				write()
			frappe.set_user("Administrator")
			self.assertEqual(_snapshot(), before)
		finally:
			frappe.set_user("Administrator")
			frappe.db.rollback(save_point=SAVEPOINT)

	def test_every_guarded_hook_refuses_the_agent(self):
		docs = {
			SETTING_DOCTYPE: frappe.get_doc(SETTING_DOCTYPE),
			CREDENTIAL_DOCTYPE: frappe.get_doc(CREDENTIAL_DOCTYPE, self.row),
		}
		frappe.set_user(AGENT_USER)
		for doctype, doc in docs.items():
			for hook in GUARDED_HOOKS:
				with self.subTest(doctype=doctype, hook=hook):
					with self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
						doc.run_method(hook, *HOOK_ARGUMENTS.get(hook, ()))

	def test_agent_cannot_insert_save_delete_setting_or_credential(self):
		def save_setting():
			doc = frappe.get_doc(SETTING_DOCTYPE)
			doc.trigger_keyword = "@forged"
			doc.save(ignore_permissions=True)

		def save_credential():
			doc = frappe.get_doc(CREDENTIAL_DOCTYPE, self.row)
			doc.note = "forged"
			doc.save(ignore_permissions=True)

		def savedocs_setting():
			doc = frappe.get_doc(SETTING_DOCTYPE).as_dict()
			doc["trigger_keyword"] = "@forged"
			savedocs(frappe.as_json(doc), "Save")

		def savedocs_credential():
			doc = frappe.get_doc(CREDENTIAL_DOCTYPE, self.row).as_dict()
			doc["note"] = "forged"
			savedocs(frappe.as_json(doc), "Save")

		paths = {
			"setting insert": lambda: frappe.get_doc(
				{"doctype": SETTING_DOCTYPE, "trigger_keyword": "@forged"}
			).insert(ignore_permissions=True),
			"setting save": save_setting,
			"setting delete": lambda: frappe.delete_doc(
				SETTING_DOCTYPE, SETTING_DOCTYPE, ignore_permissions=True
			),
			"credential insert": lambda: frappe.get_doc(_credential_dict()).insert(ignore_permissions=True),
			"credential save": save_credential,
			"credential delete": lambda: frappe.delete_doc(
				CREDENTIAL_DOCTYPE, self.row, ignore_permissions=True
			),
			"client.insert setting": lambda: frappe.client.insert(
				f'{{"doctype": "{SETTING_ESCAPED}", "trigger_keyword": "@forged"}}'
			),
			"client.insert credential": lambda: frappe.client.insert(
				json.dumps(_credential_dict()).replace(
					json.dumps(CREDENTIAL_DOCTYPE), f'"{CREDENTIAL_ESCAPED}"'
				)
			),
			"client.set_value setting": lambda: frappe.client.set_value(
				SETTING_DOCTYPE, SETTING_DOCTYPE, "trigger_keyword", "@forged"
			),
			"client.set_value credential": lambda: frappe.client.set_value(
				CREDENTIAL_DOCTYPE, self.row, "note", "forged"
			),
			"client.delete credential": lambda: frappe.client.delete(CREDENTIAL_DOCTYPE, self.row),
			"savedocs setting": savedocs_setting,
			"savedocs credential": savedocs_credential,
		}
		for path, write in paths.items():
			with self.subTest(path=path):
				self._assert_refused(write)

	def test_flag_in_client_dict_is_ignored(self):
		forged_flags = {"flags": {AGENT_WRITE_FLAG: True}, AGENT_WRITE_FLAG: 1}

		def doc_flag_and_field():
			doc = frappe.get_doc(SETTING_DOCTYPE)
			doc.flags[AGENT_WRITE_FLAG] = True
			doc.set(AGENT_WRITE_FLAG, 1)
			doc.trigger_keyword = "@forged"
			doc.save(ignore_permissions=True)

		def client_save_setting():
			doc = frappe.get_doc(SETTING_DOCTYPE).as_dict()
			doc.update(forged_flags, trigger_keyword="@forged")
			frappe.client.save(frappe.as_json(doc))

		paths = {
			"doc.flags and field": doc_flag_and_field,
			"client.save setting": client_save_setting,
			"client.insert credential": lambda: frappe.client.insert(_credential_dict(**forged_flags)),
			"credential insert": lambda: frappe.get_doc(_credential_dict(**forged_flags)).insert(
				ignore_permissions=True
			),
		}
		for path, write in paths.items():
			with self.subTest(path=path):
				self._assert_refused(write)

	def test_flag_restored_after_context_even_on_error(self):
		doc = frappe.get_doc(SETTING_DOCTYPE)
		frappe.set_user(AGENT_USER)
		with self.assertRaises(ValueError):
			with allow_agent_write():
				self.assertIs(frappe.flags.get(AGENT_WRITE_FLAG), True)
				refuse_agent_write(doc)
				raise ValueError("boom")
		self.assertIsNone(frappe.flags.get(AGENT_WRITE_FLAG))
		with self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
			refuse_agent_write(doc)

		frappe.flags[AGENT_WRITE_FLAG] = "outer"
		with allow_agent_write():
			self.assertIs(frappe.flags[AGENT_WRITE_FLAG], True)
		self.assertEqual(frappe.flags[AGENT_WRITE_FLAG], "outer")

	def test_human_system_manager_still_saves_setting(self):
		if not frappe.db.exists("User", HUMAN_USER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": HUMAN_USER,
					"first_name": "Write Guard",
					"send_welcome_email": 0,
					"roles": [{"role": "System Manager"}],
				}
			).insert(ignore_permissions=True)
		frappe.set_user(HUMAN_USER)
		refuse_agent_write(frappe.get_doc(SETTING_DOCTYPE))
		frappe.client.set_value(SETTING_DOCTYPE, SETTING_DOCTYPE, "trigger_keyword", "@guard-human")
		frappe.client.set_value(CREDENTIAL_DOCTYPE, self.row, "note", "guard-human")
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "trigger_keyword"), "@guard-human")
		self.assertEqual(frappe.db.get_value(CREDENTIAL_DOCTYPE, self.row, "note"), "guard-human")
