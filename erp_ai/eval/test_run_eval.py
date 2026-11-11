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
		metrics = compute_metrics(make_rows(TWELVE), MAPPING)

		self.assertEqual(set(metrics), METRIC_KEYS)
		self.assertEqual(metrics["labeled"], 12)
		self.assertEqual(metrics["correct"], 10)
		self.assertAlmostEqual(metrics["accuracy"], 10 / 12)
		self.assertEqual(metrics["verdict"], "70\u201385%")
		self.assertEqual(metrics["skipped_unlabeled"], 0)
		self.assertEqual(metrics["unclassified"], 0)

		expected_per_category = {
			"A": (3, 2),
			"B": (2, 2),
			"C": (2, 2),
			"D": (2, 1),
			"E": (1, 1),
			"F": (2, 2),
		}
		self.assertEqual(set(metrics["per_category"]), set(CATEGORIES))
		for c, (count, correct) in expected_per_category.items():
			cell = metrics["per_category"][c]
			self.assertEqual((cell["count"], cell["correct"]), (count, correct), c)
			self.assertAlmostEqual(cell["accuracy"], correct / count, msg=c)

		nonzero = {("A", "A"): 2, ("A", "B"): 1, ("B", "B"): 2, ("C", "C"): 2, ("D", "D"): 1, ("D", "E"): 1}
		nonzero.update({("E", "E"): 1, ("F", "F"): 2})
		self.assertEqual(set(metrics["confusion"]), set(CATEGORIES))
		for expected in CATEGORIES:
			self.assertEqual(set(metrics["confusion"][expected]), set(CATEGORIES))
			for predicted in CATEGORIES:
				self.assertEqual(
					metrics["confusion"][expected][predicted],
					nonzero.get((expected, predicted), 0),
					(expected, predicted),
				)

		self.assertEqual(metrics["top_owner"], "hieu")
		self.assertEqual(metrics["non_top_owner"]["count"], 6)
		self.assertEqual(metrics["non_top_owner"]["correct"], 4)
		self.assertAlmostEqual(metrics["non_top_owner"]["accuracy"], 4 / 6)

		report = format_report(metrics)
		self.assertIsInstance(report, str)
		self.assertIn("83.3%", report)
		self.assertIn("70\u201385%", report)
		self.assertIn("hieu", report)
		self.assertIn("D: 50.0% (1/2)", report)
		self.assertIn("  D    0   0   0   1   1   0", report)
		self.assertIn("Tickets by other authors: 66.7% (4/6)", report)
		self.assertEqual(report.count("Verdict:"), 1)

	def test_verdict_thresholds_at_85_and_70(self):
		cases = [
			(85, 100, "≥ 85%"),
			(84, 100, "70\u201385%"),
			(70, 100, "70\u201385%"),
			(69, 100, "< 70%"),
		]
		for correct, total, verdict in cases:
			with self.subTest(correct=correct, total=total):
				metrics = compute_metrics(rows_with_accuracy(correct, total), MAPPING)
				self.assertEqual(metrics["verdict"], verdict)

	def test_unparseable_and_unlabeled_rows(self):
		rows = make_rows([("A", "A", "hieu"), ("B", "B", "hieu")])
		rows.append({"ticket_type": "Type A", "predicted_category": None, "owner": "an"})
		rows.append({"ticket_type": "Type B", "owner": "an"})
		rows.append({"ticket_type": "Type A", "predicted_category": "", "owner": "an"})
		rows.append({"ticket_type": "Unknown type", "predicted_category": "A", "owner": "an"})
		rows.append({"ticket_type": "Type C", "predicted_category": "Z", "owner": "an"})

		metrics = compute_metrics(rows, MAPPING)

		self.assertEqual(metrics["skipped_unlabeled"], 1)
		self.assertEqual(metrics["labeled"], 6)
		self.assertEqual(metrics["correct"], 2)
		self.assertEqual(metrics["unclassified"], 4)
		self.assertAlmostEqual(metrics["accuracy"], 2 / 6)
		self.assertEqual(metrics["verdict"], "< 70%")
		self.assertEqual(metrics["per_category"]["A"]["count"], 3)
		self.assertEqual(metrics["per_category"]["A"]["correct"], 1)
		self.assertEqual(metrics["confusion"]["A"]["A"], 1)
		self.assertEqual(sum(sum(r.values()) for r in metrics["confusion"].values()), 2)

	def test_rows_without_ticket_type_are_unlabeled_even_if_mapping_incomplete(self):
		partial_mapping = {c: MAPPING[c] for c in "ABCDE"}
		partial_mapping["F"] = {"agent_group": "IT"}
		rows = make_rows([("A", "A", "hieu")])
		rows.append({"ticket_type": None, "predicted_category": "F", "owner": "an"})
		rows.append({"predicted_category": "F", "owner": "an"})

		metrics = compute_metrics(rows, partial_mapping)

		self.assertEqual(metrics["skipped_unlabeled"], 2)
		self.assertEqual(metrics["labeled"], 1)
		self.assertEqual(metrics["per_category"]["F"]["count"], 0)

	def test_empty_input(self):
		metrics = compute_metrics([], MAPPING)
		self.assertEqual(metrics["labeled"], 0)
		self.assertEqual(metrics["accuracy"], 0.0)
		self.assertEqual(metrics["verdict"], "< 70%")
		self.assertIsNone(metrics["top_owner"])
		self.assertIsInstance(format_report(metrics), str)
