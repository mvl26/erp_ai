import inspect
from urllib.parse import parse_qs, urlsplit

from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import change_link

NAME = "AICHG-00042"
PREFIX = f"/app/erp-ai-change-proposal/{NAME}?"


class TestChangeLink(FrappeTestCase):
	def signature(self, path):
		return path.rsplit("&_signature=", 1)[1]

	def test_path_names_the_proposal_the_action_and_a_signature(self):
		for action in ("approve", "reject"):
			path = change_link.decision_path(NAME, action)
			self.assertTrue(path.startswith(f"{PREFIX}name={NAME}&action={action}&_signature="), path)
			signature = self.signature(path)
			self.assertRegex(signature, r"^[0-9a-f]{32,}$")
			self.assertTrue(change_link.signature_ok(NAME, action, signature))

	def test_decision_path_opens_desk_form_not_api_method(self):
		for action in ("approve", "reject"):
			path = change_link.decision_path(NAME, action)
			self.assertTrue(path.startswith("/app/erp-ai-change-proposal/"), path)
			self.assertNotIn("/api/method/", path)
			parts = urlsplit(path)
			self.assertEqual(parts.path, f"/app/erp-ai-change-proposal/{NAME}")
			self.assertEqual(parts.query, change_link._signed_query(NAME, action))
		# the name is quoted in the form path, the signed query still carries the raw name
		odd = "AICHG/1 ?#&x"
		parts = urlsplit(change_link.decision_path(odd, "approve"))
		self.assertEqual(parts.path, "/app/erp-ai-change-proposal/AICHG%2F1%20%3F%23%26x")
		self.assertEqual(parse_qs(parts.query)["name"], [odd])

	def test_module_builds_no_api_method_path(self):
		# ADR-023 constraint: the form calls DECIDE_METHOD by POST, no link points at it
		self.assertNotIn("/api/method/", inspect.getsource(change_link))
		self.assertEqual(change_link.DECIDE_METHOD, "erp_ai.change_decision.decide")

	def test_signature_breaks_when_name_or_action_changes(self):
		query = parse_qs(urlsplit(change_link.decision_path(NAME, "reject")).query)
		self.assertEqual((query["name"], query["action"]), ([NAME], ["reject"]))
		(signature,) = query["_signature"]
		self.assertTrue(change_link.signature_ok(NAME, "reject", signature))
		self.assertFalse(change_link.signature_ok(NAME, "approve", signature))
		self.assertFalse(change_link.signature_ok("AICHG-00043", "reject", signature))

	def test_signature_fits_only_its_own_proposal_and_action(self):
		approve = self.signature(change_link.decision_path(NAME, "approve"))
		reject = self.signature(change_link.decision_path(NAME, "reject"))
		self.assertNotEqual(approve, reject)
		self.assertFalse(change_link.signature_ok(NAME, "reject", approve))
		self.assertFalse(change_link.signature_ok("AICHG-00043", "approve", approve))
		tampered = approve[:-1] + ("1" if approve[-1] == "0" else "0")
		self.assertFalse(change_link.signature_ok(NAME, "approve", tampered))
		for bad in ("", None, 5, ["x"], approve.upper() + "x"):
			self.assertFalse(change_link.signature_ok(NAME, "approve", bad), bad)

	def test_only_approve_and_reject_can_be_signed(self):
		for action in ("undo", "", None, "APPROVE"):
			with self.assertRaises(ValueError):
				change_link.decision_path(NAME, action)
			self.assertFalse(change_link.signature_ok(NAME, action, "0" * 64))
		for name in ("", None, 7):
			with self.assertRaises(ValueError):
				change_link.decision_path(name, "approve")
