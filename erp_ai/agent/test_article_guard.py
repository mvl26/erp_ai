from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.constants import AGENT_USER
from erp_ai.test_utils import keep_agent_settings, make_active_agent, pin_agent_roles

DRAFT_ONLY = "Bot chỉ được tạo bài CSKT ở trạng thái nháp"
NOT_OWN = "Bot không được sửa bài không do bot tạo"
NO_DELETE = "Bot không được xóa bài CSKT"
WRITE_HOOK = "erp_ai.agent.article_guard.check_article_write"
DELETE_HOOK = "erp_ai.agent.article_guard.check_article_delete"


class TestArticleGuard(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		pin_agent_roles(self)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		self.human = make_active_agent(self)

	def _article(self, user, status="Draft", **fields):
		"""Insert an HD Article of this test as `user` (session switched to `user`)."""
		frappe.set_user(user)
		values = {
			"doctype": "HD Article",
			"title": f"T40 {frappe.generate_hash(length=8)}",
			"content": "<p>Các bước đã giải quyết</p>",
			"status": status,
		}
		values.update(fields)
		return frappe.get_doc(values).insert()

	def _stored(self, name, field="status"):
		return frappe.db.get_value("HD Article", name, field)

	def assertRefused(self, message, action):
		with self.assertRaises(frappe.PermissionError) as caught:
			action()
		self.assertIn(message, str(caught.exception))

	def test_agent_insert_draft_ok(self):
		article = self._article(AGENT_USER)
		self.assertEqual(self._stored(article.name), "Draft")
		self.assertEqual(self._stored(article.name, "owner"), AGENT_USER)

		# the bot keeps editing its own draft
		article.title = f"{article.title} sửa"
		article.save()
		self.assertEqual(self._stored(article.name, "title"), article.title)

	def test_agent_publish_refused(self):
		frappe.set_user(AGENT_USER)
		for status in ("Published", "Archived"):
			with self.subTest(insert=status):
				title = f"T40 insert {status} {frappe.generate_hash(length=8)}"
				self.assertRefused(DRAFT_ONLY, lambda: self._article(AGENT_USER, status, title=title))
				self.assertFalse(frappe.db.exists("HD Article", {"title": title}))

		# ignore_permissions does not bypass the doc event
		title = f"T40 insert ignore {frappe.generate_hash(length=8)}"
		doc = frappe.get_doc(
			{"doctype": "HD Article", "title": title, "content": "<p>x</p>", "status": "Published"}
		)
		self.assertRefused(DRAFT_ONLY, lambda: doc.insert(ignore_permissions=True))
		self.assertFalse(frappe.db.exists("HD Article", {"title": title}))

		own = self._article(AGENT_USER)
		for status in ("Published", "Archived"):
			with self.subTest(update=status):
				doc = frappe.get_doc("HD Article", own.name)
				doc.status = status
				doc.flags.ignore_permissions = True
				self.assertRefused(DRAFT_ONLY, doc.save)
				self.assertEqual(self._stored(own.name), "Draft")

	def test_agent_edit_human_article_refused(self):
		human_draft = self._article(self.human)
		human_published = self._article(self.human, "Published")
		frappe.set_user(AGENT_USER)

		# a human's draft stays a draft: only the owner clause can refuse it
		doc = frappe.get_doc("HD Article", human_draft.name)
		doc.title = f"{doc.title} bot sửa"
		self.assertRefused(NOT_OWN, doc.save)
		self.assertEqual(self._stored(human_draft.name, "title"), human_draft.title)

		# un-publishing a human's article is an edit of an article the bot did not create
		doc = frappe.get_doc("HD Article", human_published.name)
		doc.status = "Draft"
		doc.flags.ignore_permissions = True
		self.assertRefused(NOT_OWN, doc.save)
		self.assertEqual(self._stored(human_published.name), "Published")

	def test_agent_delete_refused(self):
		own = self._article(AGENT_USER)
		human_draft = self._article(self.human)
		frappe.set_user(AGENT_USER)
		for name in (own.name, human_draft.name):
			with self.subTest(article=name):
				self.assertRefused(NO_DELETE, lambda: frappe.delete_doc("HD Article", name))
				self.assertRefused(
					NO_DELETE, lambda: frappe.delete_doc("HD Article", name, ignore_permissions=True)
				)
				self.assertTrue(frappe.db.exists("HD Article", name))

		# a human may still discard the bot's draft
		frappe.set_user(self.human)
		frappe.delete_doc("HD Article", own.name)
		self.assertFalse(frappe.db.exists("HD Article", own.name))

	def test_human_publishes_bot_draft(self):
		bot_draft = self._article(AGENT_USER)
		frappe.set_user(self.human)

		doc = frappe.get_doc("HD Article", bot_draft.name)
		doc.title = f"{doc.title} người duyệt"
		doc.status = "Published"
		doc.save()

		self.assertEqual(self._stored(bot_draft.name), "Published")
		self.assertEqual(self._stored(bot_draft.name, "title"), doc.title)
		self.assertEqual(self._stored(bot_draft.name, "owner"), AGENT_USER)

	def test_hooks_registered(self):
		doc_events = frappe.get_hooks("doc_events", app_name="erp_ai")
		self.assertEqual(doc_events.get("HD Article"), {"validate": [WRITE_HOOK], "on_trash": [DELETE_HOOK]})
		overrides = frappe.get_hooks("override_whitelisted_methods", app_name="erp_ai")
		self.assertEqual([method for method in overrides if method.startswith("helpdesk.")], [])
