from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import change_link

NAME = "AICHG-00042"
PREFIX = "/api/method/erp_ai.change_decision.decide?"


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
