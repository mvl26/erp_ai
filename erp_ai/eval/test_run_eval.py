import contextlib
import io
import json
import os
import tempfile
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import labels, ops_data, runner
from erp_ai.agent.classification import DEFAULT_CATEGORY_MAPPING
from erp_ai.agent.prompts import build_classify_request
from erp_ai.agent.routing import decide_route
from erp_ai.constants import CATEGORIES, LOG_DOCTYPE
from erp_ai.eval import run_eval
from erp_ai.eval.run_eval import _predict, compute_metrics, format_report
from erp_ai.eval.run_eval import run as run_eval_run
from erp_ai.gateway import GatewayError
from erp_ai.test_utils import FakeGateway, make_model_result, make_routing_rules, set_agent_settings

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
	"priority",
	"team",
	"score_distribution",
	"classify_output_tokens_max",
	"classify_max_tokens_hits",
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

	def test_priority_team_match_and_score_distribution(self):
		rows = [
			{
				"priority": "High",
				"predicted_priority": "High",
				"agent_group": "IT",
				"predicted_agent_group": "IT",
			},
			{
				"priority": "High",
				"predicted_priority": "Low",
				"agent_group": "IT",
				"predicted_agent_group": "HR",
			},
			{
				"priority": "Low",
				"predicted_priority": "Low",
				"agent_group": "HR",
				"predicted_agent_group": "HR",
			},
			# prediction None: out of the denominator of both
			{
				"priority": "Low",
				"predicted_priority": None,
				"agent_group": "IT",
				"predicted_agent_group": None,
			},
			# no label: out of both
			{"predicted_priority": "High", "predicted_agent_group": "IT"},
			{
				"priority": "",
				"predicted_priority": "High",
				"agent_group": None,
				"predicted_agent_group": "IT",
			},
		]
		for row, (complexity, importance) in zip(
			rows, [(1, 0), (1, 2), (3, 2), (None, None), (5, 7), (0, 3)], strict=True
		):
			row["predicted_complexity"] = complexity
			row["predicted_importance"] = importance

		metrics = compute_metrics(rows, MAPPING)

		for key, count, correct in (("priority", 3, 2), ("team", 3, 2)):
			cell = metrics[key]
			self.assertEqual(set(cell), {"count", "correct", "accuracy"}, key)
			self.assertEqual((cell["count"], cell["correct"]), (count, correct), key)
			self.assertAlmostEqual(cell["accuracy"], correct / count, msg=key)
		# every bin 0..3 exists, empty ones are 0; None and out-of-range values are not counted
		self.assertEqual(metrics["score_distribution"]["complexity"], {0: 1, 1: 2, 2: 0, 3: 1})
		self.assertEqual(metrics["score_distribution"]["importance"], {0: 1, 1: 0, 2: 2, 3: 1})

	def test_priority_and_team_with_no_comparable_rows(self):
		metrics = compute_metrics([{"predicted_priority": "High"}, {"priority": "High"}], MAPPING)

		self.assertEqual(metrics["priority"], {"count": 0, "correct": 0, "accuracy": 0.0})
		self.assertEqual(metrics["team"], {"count": 0, "correct": 0, "accuracy": 0.0})
		self.assertEqual(metrics["score_distribution"]["complexity"], dict.fromkeys(range(4), 0))
		self.assertEqual(metrics["score_distribution"]["importance"], dict.fromkeys(range(4), 0))

	def test_classify_token_ceiling_and_max_tokens_hits(self):
		rows = [
			{"output_tokens": 120, "stop_reason": "end_turn"},
			{"output_tokens": 600, "stop_reason": "max_tokens"},
			{"output_tokens": 350, "stop_reason": "max_tokens"},
			{"output_tokens": None, "stop_reason": None},
			{"stop_reason": "MAX_TOKENS"},
			{"output_tokens": 599, "stop_reason": "gateway_error"},
		]

		metrics = compute_metrics(rows, MAPPING)

		self.assertEqual(metrics["classify_output_tokens_max"], 600)
		self.assertEqual(metrics["classify_max_tokens_hits"], 2)
		empty = compute_metrics([], MAPPING)
		self.assertEqual((empty["classify_output_tokens_max"], empty["classify_max_tokens_hits"]), (0, 0))

	def test_report_prints_the_four_new_blocks(self):
		rows = [
			{
				"priority": "High",
				"predicted_priority": "High",
				"agent_group": "IT",
				"predicted_agent_group": "HR",
				"predicted_complexity": 2,
				"predicted_importance": 3,
				"output_tokens": 412,
				"stop_reason": "max_tokens",
			}
		]

		report = format_report(compute_metrics(rows, MAPPING))

		self.assertIn("Priority match: 100.0% (1/1)", report)
		self.assertIn("Team match: 0.0% (0/1)", report)
		self.assertIn("Complexity distribution: 0:0 1:0 2:1 3:0", report)
		self.assertIn("Importance distribution: 0:0 1:0 2:0 3:1", report)
		self.assertIn("Classify output tokens max: 412", report)
		self.assertIn("Classify max_tokens hits: 1", report)

	def test_empty_input(self):
		metrics = compute_metrics([], MAPPING)
		self.assertEqual(metrics["labeled"], 0)
		self.assertEqual(metrics["accuracy"], 0.0)
		self.assertEqual(metrics["verdict"], "< 70%")
		self.assertIsNone(metrics["top_owner"])
		self.assertIsInstance(format_report(metrics), str)


def classify_reply(category):
	return make_model_result(
		text=json.dumps({"dau_muc": category, "do_tin_cay": "Cao", "do_tin_cay_pct": 90, "ly_do": "x"})
	)


def scored_reply(category, complexity, importance, output_tokens, stop_reason="end_turn"):
	text = json.dumps(
		{
			"dau_muc": category,
			"do_tin_cay": "Cao",
			"do_tin_cay_pct": 90,
			"ly_do": "x",
			"do_phuc_tap": complexity,
			"do_quan_trong": importance,
			"ly_do_diem": "y",
		}
	)
	usage = {"input_tokens": 1, "output_tokens": output_tokens}
	return make_model_result(text=text, usage=usage, stop_reason=stop_reason)


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
		# never read the site's live mapping/routing; tests that need their own override it
		set_agent_settings(
			category_mapping=json.dumps(DEFAULT_CATEGORY_MAPPING), routing_rules=make_routing_rules()
		)
		# learning off: no lesson of the shared site reaches the runner's request (NFR-7, FEAT-008 ruling R7)
		set_agent_settings(lessons_enabled=0)
		# ADR-049: the runner's label inputs are the site's live modules and tags; the offline eval has none, so the
		# shared builder is compared without them (STD-TEST-6)
		label_patch = patch.object(labels, "classify_inputs", return_value=labels.LabelInputs())
		label_patch.start()
		self.addCleanup(label_patch.stop)

	def _write(self, rows):
		with open(self.path, "w", encoding="utf-8") as handle:
			for row in rows:
				handle.write(json.dumps(row, ensure_ascii=False) + "\n")

	def _run(self, gateway):
		with (
			patch("erp_ai.gateway.call_model", gateway),
			contextlib.redirect_stdout(io.StringIO()) as out,
		):
			metrics = run_eval_run(self.path)
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
		warning = str(logger.return_value.warning.call_args)
		self.assertIn("all_keys_failed", warning)
		self.assertIn("line 2", warning)
		self.assertNotIn(PREFIX, warning)
		self.log_error.assert_not_called()

	def test_unparseable_reply_counts_unclassified(self):
		self._write([eval_row("A"), eval_row("B")])
		gateway = FakeGateway(make_model_result(text="không phải JSON"), classify_reply("B"))

		metrics, _out = self._run(gateway)

		self.assertEqual((metrics["labeled"], metrics["correct"], metrics["unclassified"]), (2, 1, 1))

	def test_mapping_comes_from_setting_with_default_fallback(self):
		custom = {c: {**DEFAULT_CATEGORY_MAPPING[c], "ticket_type": f"Custom {c}"} for c in CATEGORIES}
		set_agent_settings(category_mapping=json.dumps(custom))
		custom_row = {**eval_row("A", predicted_category="A"), "ticket_type": "Custom A"}
		self._write([custom_row, custom_row, eval_row("A", predicted_category="A")])

		metrics, _out = self._run(FakeGateway())
		self.assertEqual((metrics["labeled"], metrics["skipped_unlabeled"]), (2, 1))

		set_agent_settings(category_mapping="")
		metrics, _out = self._run(FakeGateway())
		self.assertEqual((metrics["labeled"], metrics["skipped_unlabeled"]), (1, 2))
		self.assertEqual(metrics["per_category"]["A"]["count"], 1)

	def test_predict_returns_route_and_token_fields(self):
		gateway = FakeGateway(scored_reply("A", 2, 3, 310, "max_tokens"))

		with patch("erp_ai.gateway.call_model", gateway):
			predicted = _predict(eval_row("A"), {}, DEFAULT_CATEGORY_MAPPING)

		self.assertEqual(
			predicted,
			{
				"category": "A",
				"complexity": 2,
				"importance": 3,
				"priority": "Urgent",
				"agent_group": "IT",
				"output_tokens": 310,
				"stop_reason": "max_tokens",
			},
		)

	def test_predict_failures_give_none_fields(self):
		with patch("erp_ai.gateway.call_model", FakeGateway(GatewayError("all_keys_failed", status=529))):
			failed = _predict(eval_row("A"), {}, DEFAULT_CATEGORY_MAPPING)
		cut_off = make_model_result(
			text='{"dau_muc": "A", "do_tin', usage={"output_tokens": 600}, stop_reason="max_tokens"
		)
		with patch("erp_ai.gateway.call_model", FakeGateway(cut_off)):
			unparsed = _predict(eval_row("A"), {}, DEFAULT_CATEGORY_MAPPING)

		self.assertEqual(set(failed), set(unparsed))
		self.assertTrue(all(value is None for value in failed.values()))
		self.assertIsNone(unparsed["category"])
		self.assertIsNone(unparsed["priority"])
		self.assertEqual((unparsed["output_tokens"], unparsed["stop_reason"]), (600, "max_tokens"))

	def test_run_counts_cut_off_reply_in_token_metrics(self):
		self._write([eval_row("A"), eval_row("B")])
		cut_off = make_model_result(
			text='{"dau_muc": "A", "do_tin', usage={"output_tokens": 600}, stop_reason="max_tokens"
		)

		metrics, _out = self._run(FakeGateway(cut_off, scored_reply("B", 1, 1, 120)))

		self.assertEqual(metrics["unclassified"], 1)
		self.assertEqual(metrics["classify_output_tokens_max"], 600)
		self.assertEqual(metrics["classify_max_tokens_hits"], 1)

	def test_run_reports_priority_team_scores_and_tokens(self):
		rows = [
			eval_row("A", priority="Urgent", agent_group="IT"),
			eval_row("F", priority="Medium", agent_group="IT"),
			eval_row("B", agent_group="HR"),
		]
		set_agent_settings(
			category_mapping=json.dumps(DEFAULT_CATEGORY_MAPPING), routing_rules=make_routing_rules()
		)
		self._write(rows)
		gateway = FakeGateway(
			scored_reply("A", 1, 3, 200),
			scored_reply("F", 0, 0, 598, "max_tokens"),
			scored_reply("B", 2, 1, 150),
		)

		metrics, out = self._run(gateway)

		# A: Urgent vs Urgent; F: Low vs Medium
		self.assertEqual((metrics["priority"]["count"], metrics["priority"]["correct"]), (2, 1))
		# IT/IT, IT/IT, HR vs IT
		self.assertEqual((metrics["team"]["count"], metrics["team"]["correct"]), (3, 2))
		self.assertEqual(metrics["score_distribution"]["complexity"], {0: 1, 1: 1, 2: 1, 3: 0})
		self.assertEqual(metrics["score_distribution"]["importance"], {0: 1, 1: 1, 2: 0, 3: 1})
		self.assertEqual(metrics["classify_output_tokens_max"], 598)
		self.assertEqual(metrics["classify_max_tokens_hits"], 1)
		self.assertIn("Priority match: 50.0% (1/2)", out)

	def test_eval_uses_runner_route_function(self):
		self.assertIs(run_eval.decide_route, runner.decide_route)
		self.assertIs(run_eval.decide_route, decide_route)
		rules = make_routing_rules(departments={"Kế toán": {"team": "IT", "head": ""}})
		ticket = make_ticket(subject=f"{PREFIX}route parity", description="<p>Không in được phiếu</p>")
		# differs from the default in agent_group and priority, so a wrong `mapping` argument shows up
		entry_a = {**DEFAULT_CATEGORY_MAPPING["A"], "agent_group": "HR", "priority": "Low"}
		mapping = {**DEFAULT_CATEGORY_MAPPING, "A": entry_a}
		set_agent_settings(
			enabled=1,
			permission_level="L0",
			category_mapping=json.dumps(mapping),
			routing_rules=rules,
		)
		runner_gateway = FakeGateway(scored_reply("A", 1, 1, 100))
		with (
			patch("erp_ai.agent.runner.decide_route", wraps=decide_route) as runner_route,
			patch("erp_ai.gateway.call_model", runner_gateway),
		):
			runner.run_for_ticket(ticket.name, "ticket_insert")
		subject, description = frappe.db.get_value("HD Ticket", ticket.name, ["subject", "description"])
		self._write(
			[eval_row("A", subject=subject, description=description, priority="Low", agent_group="HR")]
		)
		eval_gateway = FakeGateway(scored_reply("A", 1, 1, 100))
		with patch("erp_ai.eval.run_eval.decide_route", wraps=decide_route) as eval_route:
			metrics, _out = self._run(eval_gateway)

		runner_route.assert_called_once()
		eval_route.assert_called_once()
		self.assertEqual(eval_route.call_args.args, runner_route.call_args.args)
		shared = {"team_exists", "is_excluded_team", "is_active_agent"}
		runner_kwargs, eval_kwargs = runner_route.call_args.kwargs, eval_route.call_args.kwargs
		# eval measures the model and the mapping, not the due-date exceptions or the D watcher (design-w0-fixes-2.md:157)
		self.assertEqual(set(eval_kwargs), shared)
		self.assertEqual(set(runner_kwargs), shared | {"due_at", "due_field_configured", "d_watcher", "now"})
		# R23a: the runner passes its probe of excluded teams (U2.md:168), eval policy.is_excluded_team itself; the
		# same keys, that one value compared by its answers
		same = shared - {"is_excluded_team"}
		self.assertEqual({k: eval_kwargs[k] for k in same}, {k: runner_kwargs[k] for k in same})
		excluded = f"{PREFIX}nhóm loại trừ"
		set_agent_settings(excluded_teams=excluded)
		for kwargs in (eval_kwargs, runner_kwargs):
			self.assertEqual([kwargs["is_excluded_team"](team) for team in (excluded, "IT")], [True, False])
		self.assertEqual(eval_route.call_args.args[2], mapping)
		expected = build_classify_request(subject, description, ("Kế toán",))
		self.assertEqual(eval_gateway.calls[0]["system"], expected["system"])
		self.assertEqual(runner_gateway.calls[0]["system"], expected["system"])
		# importance 1 adds no priority floor, so Low/HR can only come from the seeded mapping
		self.assertEqual((metrics["priority"]["count"], metrics["priority"]["correct"]), (1, 1))
		self.assertEqual((metrics["team"]["count"], metrics["team"]["correct"]), (1, 1))

	def test_malformed_line_names_its_line_number(self):
		with open(self.path, "w", encoding="utf-8") as handle:
			handle.write(json.dumps(eval_row("A", predicted_category="A")) + "\n{not json\n")

		with self.assertRaises(ValueError) as ctx:
			self._run(FakeGateway())

		self.assertIn("line 2", str(ctx.exception))


class TestCategoryRuleShared(FrappeTestCase):
	"""run_eval and ops_data must put a ticket type in the same category (design-w0-fixes-2 section 3)."""

	def test_expected_category_agrees_with_ops_data(self):
		colliding = {"C": {"ticket_type": "X"}, "A": {"ticket_type": "X"}, "B": {"ticket_type": "Y"}}
		mappings = {
			"colliding": colliding,
			"colliding, keys reversed": dict(reversed(list(colliding.items()))),
			"default": DEFAULT_CATEGORY_MAPPING,
		}
		for label, mapping in mappings.items():
			reverse_map = ops_data.category_by_ticket_type(mapping)
			ticket_types = [entry.get("ticket_type") for entry in mapping.values()] + ["", "Unknown"]
			for ticket_type in ticket_types:
				with self.subTest(mapping=label, ticket_type=ticket_type):
					self.assertEqual(
						run_eval._expected_category(ticket_type, mapping),
						ops_data.ticket_category({"ticket_type": ticket_type}, reverse_map),
					)
