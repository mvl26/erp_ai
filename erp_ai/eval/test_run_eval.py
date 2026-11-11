from frappe.tests.utils import FrappeTestCase

from erp_ai.constants import CATEGORIES
from erp_ai.eval.run_eval import compute_metrics, format_report

METRIC_KEYS = {
	"labeled",
	"correct",
	"accuracy",
	"per_category",
	"confusion",
	"unclassified",
	"top_owner",
	"non_top_owner",
	"verdict",
	"skipped_unlabeled",
}

MAPPING = {c: {"ticket_type": f"Type {c}", "agent_group": "IT", "priority": "Medium"} for c in CATEGORIES}

# (expected category, predicted category, owner)
TWELVE = [
	("A", "A", "hieu"),
	("A", "A", "hieu"),
	("A", "B", "an"),
	("B", "B", "hieu"),
	("B", "B", "an"),
	("C", "C", "hieu"),
	("C", "C", "binh"),
	("D", "D", "hieu"),
	("D", "E", "an"),
	("E", "E", "hieu"),
	("F", "F", "an"),
	("F", "F", "binh"),
]


def make_rows(spec):
	return [
		{"ticket_type": MAPPING[expected]["ticket_type"], "predicted_category": predicted, "owner": owner}
		for expected, predicted, owner in spec
	]


def rows_with_accuracy(correct, total):
	spec = [("A", "A" if i < correct else "B", "hieu") for i in range(total)]
	return make_rows(spec)


class TestRunEval(FrappeTestCase):
	def test_metrics_twelve_ticket_sample(self):
		m = compute_metrics(make_rows(TWELVE), MAPPING)

		self.assertEqual(set(m), METRIC_KEYS)
		self.assertEqual(m["labeled"], 12)
		self.assertEqual(m["correct"], 10)
		self.assertAlmostEqual(m["accuracy"], 10 / 12)
		self.assertEqual(m["verdict"], "70\u201385%")
		self.assertEqual(m["skipped_unlabeled"], 0)
		self.assertEqual(m["unclassified"], 0)

		expected_per_category = {
			"A": (3, 2),
			"B": (2, 2),
			"C": (2, 2),
			"D": (2, 1),
			"E": (1, 1),
			"F": (2, 2),
		}
		self.assertEqual(set(m["per_category"]), set(CATEGORIES))
		for c, (count, correct) in expected_per_category.items():
			cell = m["per_category"][c]
			self.assertEqual((cell["count"], cell["correct"]), (count, correct), c)
			self.assertAlmostEqual(cell["accuracy"], correct / count, msg=c)

		nonzero = {("A", "A"): 2, ("A", "B"): 1, ("B", "B"): 2, ("C", "C"): 2, ("D", "D"): 1, ("D", "E"): 1}
		nonzero.update({("E", "E"): 1, ("F", "F"): 2})
		self.assertEqual(set(m["confusion"]), set(CATEGORIES))
		for expected in CATEGORIES:
			self.assertEqual(set(m["confusion"][expected]), set(CATEGORIES))
			for predicted in CATEGORIES:
				self.assertEqual(
					m["confusion"][expected][predicted],
					nonzero.get((expected, predicted), 0),
					(expected, predicted),
				)

		self.assertEqual(m["top_owner"], "hieu")
		self.assertEqual(m["non_top_owner"]["count"], 6)
		self.assertEqual(m["non_top_owner"]["correct"], 4)
		self.assertAlmostEqual(m["non_top_owner"]["accuracy"], 4 / 6)

		report = format_report(m)
		self.assertIsInstance(report, str)
		self.assertIn("83.3%", report)
		self.assertIn("70\u201385%", report)
		self.assertIn("hieu", report)

	def test_verdict_thresholds_at_85_and_70(self):
		cases = [
			(85, 100, "≥ 85%"),
			(84, 100, "70\u201385%"),
			(70, 100, "70\u201385%"),
			(69, 100, "< 70%"),
		]
		for correct, total, verdict in cases:
			with self.subTest(correct=correct, total=total):
				m = compute_metrics(rows_with_accuracy(correct, total), MAPPING)
				self.assertEqual(m["verdict"], verdict)

	def test_unparseable_and_unlabeled_rows(self):
		rows = make_rows([("A", "A", "hieu"), ("B", "B", "hieu")])
		rows.append({"ticket_type": "Type A", "predicted_category": None, "owner": "an"})
		rows.append({"ticket_type": "Type B", "owner": "an"})
		rows.append({"ticket_type": "Type A", "predicted_category": "", "owner": "an"})
		rows.append({"ticket_type": "Unknown type", "predicted_category": "A", "owner": "an"})
		rows.append({"ticket_type": "Type C", "predicted_category": "Z", "owner": "an"})

		m = compute_metrics(rows, MAPPING)

		self.assertEqual(m["skipped_unlabeled"], 1)
		self.assertEqual(m["labeled"], 6)
		self.assertEqual(m["correct"], 2)
		self.assertEqual(m["unclassified"], 4)
		self.assertAlmostEqual(m["accuracy"], 2 / 6)
		self.assertEqual(m["verdict"], "< 70%")
		self.assertEqual(m["per_category"]["A"]["count"], 3)
		self.assertEqual(m["per_category"]["A"]["correct"], 1)
		self.assertEqual(m["confusion"]["A"]["A"], 1)
		self.assertEqual(sum(sum(r.values()) for r in m["confusion"].values()), 2)

	def test_empty_input(self):
		m = compute_metrics([], MAPPING)
		self.assertEqual(m["labeled"], 0)
		self.assertEqual(m["accuracy"], 0.0)
		self.assertEqual(m["verdict"], "< 70%")
		self.assertIsNone(m["top_owner"])
		self.assertIsInstance(format_report(m), str)
