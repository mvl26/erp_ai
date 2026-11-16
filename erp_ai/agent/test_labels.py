import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import labels
from erp_ai.test_utils import keep_agent_settings, set_agent_settings

PREFIX = "ERPAI-TEST-"
# Labels only these tests give, so the counts never meet the shared site's own tags (STD-TEST-6).
KHO = f"{PREFIX}Kho"
IN_AN = f"{PREFIX}In ấn"
NHAN_SU = f"{PREFIX}Nhân sự"
EXCLUDED_TEAM = "T49 Nhóm loại trừ"


def tag(ticket, *names):
	doc = frappe.get_doc("HD Ticket", ticket)
	for name in names:
		doc.add_tag(name)


class LabelsCase(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)

	def _ticket(self, subject, *names):
		# no prefix in the subject: its words would make every test ticket alike
		name = make_ticket(subject=subject, description="<p>x</p>").name
		tag(name, *names)
		return name

	def _inputs(self, ticket, subject, description="<p>x</p>"):
		return labels.classify_inputs(ticket, subject, description)

	def _ours(self, catalog):
		return [row for row in catalog if row[0].startswith(PREFIX)]


class TestParseTags(FrappeTestCase):
	def test_tags_column_read_without_empty_and_helpdesk_tags(self):
		self.assertEqual(labels.parse_tags(",First Ticket,Stock, In ấn ,,"), ["Stock", "In ấn"])
		self.assertEqual(labels.parse_tags(None), [])
		self.assertEqual(labels.parse_tags(""), [])
		self.assertIn("First Ticket", labels.IGNORED_LABELS)


class TestModuleLabels(FrappeTestCase):
	def test_modules_of_the_installed_apps_without_the_bot_module(self):
		modules = labels.module_labels()
		for name in ("Stock", "HR", "Accounts", "Helpdesk"):
			self.assertIn(name, modules)
		self.assertNotIn("ERP AI agent", modules)
		self.assertEqual(list(modules), sorted(modules, key=str.casefold))
		self.assertIsInstance(modules, tuple)


class TestCanonical(FrappeTestCase):
	def test_module_spelling_wins_others_kept(self):
		self.assertEqual(
			labels.canonical(("stock", "Delivery Note", "hr"), ("HR", "Stock")),
			("Stock", "Delivery Note", "HR"),
		)
		self.assertEqual(labels.canonical((), ("Stock",)), ())
		# Helpdesk's own tag is never a label the bot gives
		self.assertEqual(labels.canonical(("first ticket", "Stock"), ()), ("Stock",))


class TestClassifyInputs(LabelsCase):
	def test_modules_are_the_module_labels(self):
		current = self._ticket("phiếu mới")
		self.assertEqual(self._inputs(current, "phiếu mới").modules, labels.module_labels())

	def test_alike_ticket_gives_its_labels_unrelated_one_not(self):
		alike = self._ticket("Không in được Phiếu xuất kho Delivery Note", KHO, IN_AN)
		self._ticket("Tạo tài khoản nhân viên mới", NHAN_SU)
		current = self._ticket("Lỗi in Phiếu xuất kho", KHO)

		inputs = self._inputs(current, "Lỗi in Phiếu xuất kho", "<p>Bấm in Delivery Note thì báo lỗi</p>")

		self.assertEqual(
			[row for row in inputs.similar_labels if any(label.startswith(PREFIX) for label in row[1])],
			[(frappe.db.get_value("HD Ticket", alike, "subject"), (KHO, IN_AN))],
		)

	def test_common_words_alone_make_no_alike_ticket(self):
		self._ticket("không được phiếu của", KHO)
		current = self._ticket("x")

		inputs = self._inputs(current, "Không duyệt được phiếu của tôi")

		self.assertEqual([row for row in inputs.similar_labels if KHO in row[1]], [])

	def test_the_ticket_itself_is_never_alike(self):
		current = self._ticket("Máy in kho hỏng hẳn", KHO)
		inputs = self._inputs(current, "Máy in kho hỏng hẳn")
		self.assertEqual([row for row in inputs.similar_labels if KHO in row[1]], [])

	def test_most_shared_words_first_then_newest_at_most_five(self):
		self._ticket("bảng lương tháng mười", f"{PREFIX}yếu")
		for index in range(6):
			self._ticket(f"bảng lương tháng mười hai thưởng tết {index}", f"{PREFIX}mạnh{index}")
		current = self._ticket("x")

		inputs = self._inputs(current, "bảng lương tháng mười hai thưởng tết")

		ours = [row for row in inputs.similar_labels if row[1][0].startswith(PREFIX)]
		self.assertEqual(labels.SIMILAR_MAX, 5)
		# the six strong ones (7 shared words) tie, the newest five come first; the weak one (4) is left out
		self.assertEqual([row[1] for row in ours], [(f"{PREFIX}mạnh{index}",) for index in (5, 4, 3, 2, 1)])

	def test_catalog_counts_tickets_per_label_with_its_description(self):
		self._ticket("a", KHO, IN_AN)
		self._ticket("b", KHO)
		current = self._ticket("c", KHO)
		frappe.db.set_value("Tag", KHO, "description", "Phiếu về kho")

		inputs = self._inputs(current, "c")

		# the ticket being classified is not counted
		self.assertEqual(self._ours(inputs.label_catalog), [(KHO, 2, "Phiếu về kho"), (IN_AN, 1, "")])
		self.assertNotIn("First Ticket", [row[0] for row in inputs.label_catalog])

	def test_catalog_is_capped(self):
		current = self._ticket("c")
		names = [f"{PREFIX}n{index:02d}" for index in range(labels.CATALOG_MAX + 2)]
		self._ticket("a", *names)
		self.assertLessEqual(len(self._inputs(current, "c").label_catalog), labels.CATALOG_MAX)
		self.assertEqual(labels.CATALOG_MAX, 40)

	def test_excluded_tickets_give_no_label_and_no_count(self):
		set_agent_settings(excluded_teams=EXCLUDED_TEAM)
		if not frappe.db.exists("HD Team", EXCLUDED_TEAM):
			frappe.get_doc(
				{"doctype": "HD Team", "team_name": EXCLUDED_TEAM, "users": [{"user": "Administrator"}]}
			).insert(ignore_permissions=True)
		hidden = self._ticket("Bảng lương bí mật tháng mười", f"{PREFIX}Mật")
		frappe.db.set_value("HD Ticket", hidden, "agent_group", EXCLUDED_TEAM)
		current = self._ticket("x")

		inputs = self._inputs(current, "Bảng lương bí mật tháng mười")

		self.assertNotIn(f"{PREFIX}Mật", [row[0] for row in inputs.label_catalog])
		self.assertEqual([row for row in inputs.similar_labels if f"{PREFIX}Mật" in row[1]], [])
