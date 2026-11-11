import contextlib
import io
import json
import os
import tempfile
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import runner
from erp_ai.agent.classification import DEFAULT_CATEGORY_MAPPING
from erp_ai.agent.prompts import build_classify_request
from erp_ai.constants import CATEGORIES, LOG_DOCTYPE
from erp_ai.eval import run_eval
from erp_ai.eval.run_eval import compute_metrics, format_report
from erp_ai.gateway import GatewayError
from erp_ai.test_utils import FakeGateway, make_model_result, set_agent_settings

PREFIX = "ERPAI-TEST-"

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


def classify_reply(category):
	return make_model_result(text=json.dumps({"dau_muc": category, "do_tin_cay": "Cao", "ly_do": "x"}))


def eval_row(category, **extra):
	return {
		"subject": f"{PREFIX}{category}",
		"description": "mô tả",
		"ticket_type": DEFAULT_CATEGORY_MAPPING[category]["ticket_type"],
		"owner": "an",
		**extra,
	}


class TestRunEvalRun(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		error_log = patch.object(frappe, "log_error")
		self.log_error = error_log.start()
		self.addCleanup(error_log.stop)
		tmp = tempfile.TemporaryDirectory()
		self.addCleanup(tmp.cleanup)
		self.path = os.path.join(tmp.name, "labeled.jsonl")

	def _write(self, rows):
		with open(self.path, "w", encoding="utf-8") as handle:
			for row in rows:
				handle.write(json.dumps(row, ensure_ascii=False) + "\n")

	def _run(self, gateway):
		with (
			patch("erp_ai.gateway.call_model", gateway),
			contextlib.redirect_stdout(io.StringIO()) as out,
		):
			metrics = run_eval.run(self.path)
		return metrics, out.getvalue()

	def test_run_uses_given_predictions_without_gateway(self):
		self._write([eval_row("A", predicted_category="A"), eval_row("B", predicted_category="C")])
		gateway = FakeGateway()

		metrics, _out = self._run(gateway)

		self.assertEqual(gateway.call_count, 0)
		self.assertEqual((metrics["labeled"], metrics["correct"]), (2, 1))

	def test_run_classifies_rows_without_prediction_and_prints_report(self):
		self._write([eval_row("A"), eval_row("B", predicted_category="B"), eval_row("C")])
		gateway = FakeGateway(classify_reply("A"), classify_reply("D"))

		metrics, out = self._run(gateway)

		self.assertEqual(gateway.call_count, 2)
		self.assertEqual(gateway.calls[0]["task"], "classify")
		self.assertEqual((metrics["labeled"], metrics["correct"]), (3, 2))
		self.assertEqual(metrics["confusion"]["C"]["D"], 1)
		self.assertEqual(out.strip(), format_report(metrics))

	def test_eval_and_runner_share_classify_request(self):
		ticket = make_ticket(subject=f"{PREFIX}share request", description="<p>Không in được phiếu</p>")
		set_agent_settings(
			enabled=1, permission_level="L0", category_mapping=json.dumps(DEFAULT_CATEGORY_MAPPING)
		)
		runner_gateway = FakeGateway(classify_reply("A"))
		with patch("erp_ai.gateway.call_model", runner_gateway):
			runner.run_for_ticket(ticket.name, "ticket_insert")
		subject, description = frappe.db.get_value("HD Ticket", ticket.name, ["subject", "description"])
		self._write([eval_row("A", subject=subject, description=description)])
		eval_gateway = FakeGateway(classify_reply("A"))

		self._run(eval_gateway)

		self.assertEqual(runner_gateway.call_count, 1)
		self.assertEqual(eval_gateway.call_count, 1)
		expected = build_classify_request(subject, description)
		for call in (runner_gateway.calls[0], eval_gateway.calls[0]):
			self.assertEqual(call["system"], expected["system"])
			self.assertEqual(call["messages"], expected["messages"])
		self.assertEqual(eval_gateway.calls[0]["max_tokens"], runner_gateway.calls[0]["max_tokens"])

	def test_run_writes_no_log_and_touches_no_ticket(self):
		ticket = make_ticket(subject=f"{PREFIX}untouched")
		before_ticket = frappe.db.get_value("HD Ticket", ticket.name, ["modified", "ticket_type", "priority"])
		self._write([eval_row("A"), eval_row("B")])
		logs_before = frappe.db.count(LOG_DOCTYPE)
		tickets_before = frappe.db.count("HD Ticket")

		self._run(FakeGateway(classify_reply("A"), classify_reply("B")))

		self.assertEqual(frappe.db.count(LOG_DOCTYPE), logs_before)
		self.assertEqual(frappe.db.count("HD Ticket"), tickets_before)
		self.assertEqual(
			frappe.db.get_value("HD Ticket", ticket.name, ["modified", "ticket_type", "priority"]),
			before_ticket,
		)
		self.log_error.assert_not_called()

	def test_gateway_error_on_one_row_counts_unclassified_and_run_continues(self):
		self._write([eval_row("A"), eval_row("B"), eval_row("C")])
		gateway = FakeGateway(
			classify_reply("A"), GatewayError("all_keys_failed", status=529), classify_reply("C")
		)

		with patch.object(frappe, "logger") as logger:
			metrics, _out = self._run(gateway)

		self.assertEqual(gateway.call_count, 3)
		self.assertEqual((metrics["labeled"], metrics["correct"], metrics["unclassified"]), (3, 2, 1))
		logger.return_value.warning.assert_called_once()
		self.assertIn("all_keys_failed", str(logger.return_value.warning.call_args))
		self.log_error.assert_not_called()

	def test_unparseable_reply_counts_unclassified(self):
		self._write([eval_row("A"), eval_row("B")])
		gateway = FakeGateway(make_model_result(text="không phải JSON"), classify_reply("B"))

		metrics, _out = self._run(gateway)

		self.assertEqual((metrics["labeled"], metrics["correct"], metrics["unclassified"]), (2, 1, 1))

	def test_mapping_comes_from_setting_with_default_fallback(self):
		custom = {c: {**DEFAULT_CATEGORY_MAPPING[c], "ticket_type": f"Custom {c}"} for c in CATEGORIES}
		set_agent_settings(category_mapping=json.dumps(custom))
		self._write(
			[
				{**eval_row("A", predicted_category="A"), "ticket_type": "Custom A"},
				eval_row("A", predicted_category="A"),
			]
		)

		metrics, _out = self._run(FakeGateway())
		self.assertEqual((metrics["labeled"], metrics["skipped_unlabeled"]), (1, 1))

		set_agent_settings(category_mapping="")
		metrics, _out = self._run(FakeGateway())
		self.assertEqual((metrics["labeled"], metrics["skipped_unlabeled"]), (1, 1))
		self.assertEqual(metrics["per_category"]["A"]["count"], 1)
